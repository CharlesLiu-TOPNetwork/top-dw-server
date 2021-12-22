#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class MetricsAlarmConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("MetricsAlarmConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 1

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.metrics_alarm_template = {
            "send_timestamp": 0,
            "public_ip": "",
            "category": "",
            "tag": "",
            "kv_content": "",
        }
        # self.cache_num = 1
        # self.alarm_insert_cache = {
        # }
        self.tag_cache = {
          # env: [(category,tag)]
        }
        # self.ip_cache = {
        # }

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
                if alarm_type == 'metrics_alarm':
                    # slog.info(alarm_payload.get('packet'))
                    self.metrics_alarm_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'metrics_alarm':
                        self.metrics_alarm_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def metrics_alarm_handle(self, packet):
        # slog.info(packet)
        '''
        {
            "alarm_type": "metrics_alarm",
            "packet": {
                "send_timestamp": 1627521612,
                "env": "database_name",
                "public_ip": "123.123.123.123",
                'category': 'category', 
                'tag': 'tag', 
                "kv_content": {
                    "src_node_id": "f60000ff040003ff.0180000000000000",
                    "dst_node_id": "2acfffff0102e664.a7faaa0fde346d82",
                    "hop_num": 0,
                    "msg_hash": 3765266419,
                    "msg_size": 1779,
                    "is_root": 1,
                    "is_broadcast": 1,
                    "is_pulled": 0,
                    "packet_size": 0,
                    "timestamp": 1627467361822
                }
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.metrics_alarm_template)
        item['send_timestamp'] = packet.get('send_timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['category'] = packet.get('category')
        item['tag'] = packet.get('tag')
        item['kv_content'] = json.dumps(packet.get('kv_content'), separators=(',', ':'))
        self.mysql_db.insert_into_db(db, "metrics_alarm", item)


        if db not in self.tag_cache:
            self.tag_cache[db] = []
        full_tag = packet.get('category')+'__'+packet.get('tag')
        if full_tag not in self.tag_cache[db]:
            self.tag_cache[db].append(full_tag)
            self.mysql_db.insert_ingore_into_db(db, "tags_table", {'category': packet.get('category'), 'tag': packet.get('tag'), 'type': "alarm"})
        
        # tags = {}
        # tags['category'] = packet.get('category')
        # tags['tag'] = packet.get('tag')
        # tags['type'] = "alarm"
        # self.mysql_db.insert_ingore_into_db(db, "tags_table", tags)

        return True
