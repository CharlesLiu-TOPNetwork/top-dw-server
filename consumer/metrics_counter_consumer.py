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
        self.cache_num = 1000
        self.counter_insert_cache = {
        }
        self.tag_cache = {
          # env: [(category,tag)]
        }
        self.ip_cache = {
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

    def metrics_counter_handle(self, packet):
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


        if db not in self.counter_insert_cache:
            self.counter_insert_cache[db] = []
        self.counter_insert_cache[db].append(item)

        if db not in self.tag_cache:
            self.tag_cache[db] = []
        full_tag = packet.get('category')+'__'+packet.get('tag')
        if full_tag not in self.tag_cache[db]:
            self.tag_cache[db].append(full_tag)
            self.mysql_db.insert_ingore_into_db(db, "tags_table", {'category': packet.get('category'), 'tag': packet.get('tag'), 'type': "counter"})
        
        if db not in self.ip_cache:
            self.ip_cache[db] = []
        if packet.get('public_ip') not in self.ip_cache[db]:
            self.ip_cache[db].append(packet.get('public_ip'))
            self.mysql_db.insert_ingore_into_db(db,"ips_table",{'public_ips':packet.get('public_ip')})

        if len(self.counter_insert_cache[db]) > self.cache_num:
            self.mysql_db.multi_insert_into_db(db,"metrics_counter",self.counter_insert_cache[db])
            self.counter_insert_cache[db] = []

        # self.mysql_db.insert_into_db(db, "metrics_counter", item)

        # ips = {}
        # ips['public_ips'] = packet.get('public_ip')
        # self.mysql_db.insert_ingore_into_db(db, "ips_table", ips)

        # tags = {}
        # tags['category'] = packet.get('category')
        # tags['tag'] = packet.get('tag')
        # tags['type'] = "counter"
        # self.mysql_db.insert_ingore_into_db(db, "tags_table", tags)


        return True
