#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class MetricsCounterConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("MetricsCounterConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.counter_metrics_template = {
            "send_timestamp": 0,
            "public_ip": "",
            "category": "",
            "tag": "",
            "count": 0,
            "value": 0
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
                slog.info(alarm_payload)
                if alarm_type == 'metrics_counter':
                    slog.info(alarm_payload.get('packet'))
                    self.metrics_counter_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'metrics_counter':
                        self.metrics_counter_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    # focus on packet_info(drop_rate,hop_num,timing)
    def metrics_counter_handle(self, packet):
        now = int(time.time() * 1000)
        slog.info(packet)
        '''
        {
            'alarm_type': 'metrics_counter', 
            'packet': {
                'env': 'test2', 
                'public_ip': '192.168.181.128', 
                'send_timestamp': 1624513771, 
                'category': 'dataobject', 
                'tag': 'xreceiptid_pair_t', 
                'count': 960, 
                'value': 2
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.counter_metrics_template)
        item['send_timestamp'] = packet.get('send_timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['category'] = packet.get('category')
        item['tag'] = packet.get('tag')
        item['count'] = packet.get('count')
        item['value'] = packet.get('value')

        self.mysql_db.insert_into_db(db, "metrics_counter", item)

        return True
