#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class P2PTestSendRecordConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("P2PTestSendRecordConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 30

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.p2ptest_sendrecord_template = {
            "send_timestamp": 0,
            "src_ip":"",
            "dst_ip":"",
            "msg_hash" : "",
            "src_node_id": "",
            "dst_node_id": "",
            "hop_num":0,
            "msg_size":0,
            "is_root":0,
            "is_broadcast":0,
        }
        self.cache_num = 1000
        self.p2ptest_send_record_cache = {
        }
        self.ip_cache = {}

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
            if alarm_payload_list :
                for alarm_payload in alarm_payload_list:
                    alarm_type = alarm_payload.get('alarm_type')
                    slog.info(alarm_payload)
                    if alarm_type == 'p2ptest_sendrecord':
                        slog.info(alarm_payload.get('packet'))
                        self.p2ptest_sendrecord_handle(alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            else:
                self.p2ptest_try_store_cache()
        return

    def consume_alarm(self):
        while True:
            slog.info("begin consume_alarm alarm_queue.size is {0}".format(
                self.alarm_queue_.qsize(self.queue_key_list_)))
            try:
                alarm_payload_list = self.alarm_queue_.get_queue_exp(
                    self.queue_key_list_, self.consume_step_)  # return dict or None
                if alarm_payload_list :
                    for alarm_payload in alarm_payload_list:
                        alarm_type = alarm_payload.get('alarm_type')
                        if alarm_type == 'p2ptest_sendrecord':
                            self.p2ptest_sendrecord_handle(
                                alarm_payload.get('packet'))
                        else:
                            slog.warn('invalid alarm_type:{0}'.format(alarm_type))
                else:
                    self.p2ptest_try_store_cache()
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def p2ptest_sendrecord_handle(self, packet):
        slog.info(packet)
        '''
        {
            "alarm_type": "p2ptest_sendrecord",
            "packet": {
                "env": "test_database_name",
                "public_ip": "192.168.181.128",
                "src_node_id": "23afffffa02048c9.0fe027cb6e6cbabe",
                "dst_node_id": "90cfffff637c2db9.0a007e26a0ebd6b9",
                "dst_ip_port": "192.168.50.142:9126",
                "hop_num": 0,
                "msg_hash": 2523515927,
                "msg_size": 0,
                "is_root": 1,
                "is_broadcast": 1,
                "timestamp": 1638785153597
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.p2ptest_sendrecord_template)
        item['send_timestamp'] = packet.get('timestamp')
        item['msg_hash'] = packet.get('msg_hash')
        item['src_ip'] = packet.get('public_ip')
        item['dst_ip'] = packet.get('dst_ip_port')
        item['src_node_id'] = packet.get('src_node_id')
        item['dst_node_id'] = packet.get('dst_node_id')
        item['hop_num'] = packet.get('hop_num')
        item['msg_size'] = packet.get('msg_size')
        item['is_root'] = packet.get('is_root')
        item['is_broadcast'] = packet.get('is_broadcast')
        
        if db not in self.p2ptest_send_record_cache:
            self.p2ptest_send_record_cache[db] = []
        self.p2ptest_send_record_cache[db].append(item)

        # self.mysql_db.insert_into_db(db, "p2ptest_send_record", item)

        if db not in self.ip_cache:
            self.ip_cache[db] = []
        if packet.get('public_ip') not in self.ip_cache[db]:
            self.ip_cache[db].append(packet.get('public_ip'))
            self.mysql_db.insert_ingore_into_db(db,"ips_table",{'public_ips':packet.get('public_ip')})

        # ips = {}
        # ips['public_ips'] = packet.get('public_ip')
        # self.mysql_db.insert_ingore_into_db(db, "ips_table", ips)


        if len(self.p2ptest_send_record_cache[db]) > self.cache_num:
            self.mysql_db.multi_insert_into_db(db,"p2ptest_send_record",self.p2ptest_send_record_cache[db])
            self.p2ptest_send_record_cache[db] = []


        return True

    def p2ptest_try_store_cache(self):
        for _db,_cache in self.p2ptest_send_record_cache.items():
            if len(_cache) > 0:
                self.mysql_db.multi_insert_into_db(_db,"p2ptest_send_record",_cache)
                self.p2ptest_send_record_cache[_db] = []
