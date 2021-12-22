#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class MetricsFlowConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("MetricsFlowConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.flow_metrics_template = {
            "send_timestamp": 0,
            "public_ip": "",
            "category": "",
            "tag": "",
            "count": 0,
            "max_flow": 0,
            "min_flow": 0,
            "sum_flow": 0,
            "avg_flow":0,
            "tps_flow":0,
            "tps": 0,
        }

        return

    def run(self):
        # usually for one consumer , only handle one type
        slog.info('consume_alarm run')
        if self.alarm_env_ == 'test':
            self.consume_alarm_with_notry()
        else:
            self.consume_alarm()
        return

    def consume_alarm_with_notry(self):
        while True:
            # slog.info("begin consume_alarm_with_notry alarm_queue.size is {0}".format(self.alarm_queue_.qsize(self.queue_key_list_)))
            alarm_payload_list = self.alarm_queue_.get_queue_exp(
                self.queue_key_list_, self.consume_step_)  # return dict or None
            for alarm_payload in alarm_payload_list:
                alarm_type = alarm_payload.get('alarm_type')
                # slog.info(alarm_payload)
                if alarm_type == 'metrics_flow':
                    # slog.info(alarm_payload.get('packet'))
                    self.metrics_flow_handle(alarm_payload.get('packet'))
                else:
                    slog.warn('invalid alarm_type:{0}'.format(alarm_type))
        return

    def consume_alarm(self):
        while True:
            slog.info("begin consume_alarm alarm_queue.size is {0}".format(
                self.alarm_queue_.qsize(self.queue_key_list_)))
            try:
                alarm_payload_list = self.alarm_queue_.get_queue_exp(
                    self.queue_key_list_, self.consume_step_)  # return dict or None
                for alarm_payload in alarm_payload_list:
                    alarm_type = alarm_payload.get('alarm_type')
                    if alarm_type == 'metrics_flow':
                        self.metrics_flow_handle(alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def metrics_flow_handle(self, packet):
        # slog.info(packet)
        '''
        {
            'alarm_type': 'metrics_flow', 
            'packet': {
                'env': 'test2', 
                'public_ip': '192.168.181.128', 
                'send_timestamp': 1624513771, 
                'category': 'vhost', 'tag': 
                'handle_data_ready_called', 
                'count': 3340, 
                'max_flow': 10, 
                'min_flow': 1, 
                'sum_flow': 4146, 
                'avg_flow': 1, 
                'tps_flow': 1683, 
                'tps': '9.34'
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.flow_metrics_template)
        item['send_timestamp'] = packet.get('send_timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['category'] = packet.get('category')
        item['tag'] = packet.get('tag')
        item['count'] = packet.get('count')
        item['max_flow'] = packet.get('max_flow')
        item['min_flow'] = packet.get('min_flow')
        item['sum_flow'] = packet.get('sum_flow')
        item['avg_flow'] = packet.get('avg_flow')
        item['tps_flow'] = packet.get('tps_flow')
        item['tps'] = packet.get('tps')

        self.mysql_db.insert_into_db(db, "metrics_flow", item)

        
        tags = {}
        tags['category'] = packet.get('category')
        tags['tag'] = packet.get('tag')
        tags['type'] = "flow"
        self.mysql_db.insert_ingore_into_db(db, "tags_table", tags)

        return True
