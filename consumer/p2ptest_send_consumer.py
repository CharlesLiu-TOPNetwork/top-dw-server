#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class P2PTestSendConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("P2PTestSendConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.p2ptest_send_template = {
            "send_timestamp": 0,
            "src_ip":"",
            "msg_hash" : "",
            "src_node_id": "",
            "dst_node_id": "",
            "hop_num":0,
            "msg_size":0,
            "is_root":0,
            "is_broadcast":0,
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
                if alarm_type == 'p2ptest_send_info':
                    slog.info(alarm_payload.get('packet'))
                    self.p2ptest_send_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'p2ptest_send_info':
                        self.p2ptest_send_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def p2ptest_send_handle(self, packet):
        slog.info(packet)
        '''
        {
            "alarm_type": "p2ptest_send_info",
            "packet": {
                "env": "test_database_name",
                "public_ip": "192.168.181.128",
                "src_node_id": "23afffffa02048c9.0fe027cb6e6cbabe",
                "dst_node_id": "c9cfffffc2b35dff.bdf5ed38df1613e0",
                "hop_num": 0,
                "msg_hash": 2523515927,
                "msg_size": 0,
                "is_root": 1,
                "is_broadcast": 1,
                "timestamp": 1638785153596
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.p2ptest_send_template)
        item['send_timestamp'] = packet.get('timestamp')
        item['msg_hash'] = packet.get('msg_hash')
        item['src_ip'] = packet.get('public_ip')
        item['src_node_id'] = packet.get('src_node_id')
        item['dst_node_id'] = packet.get('dst_node_id')
        item['hop_num'] = packet.get('hop_num')
        item['msg_size'] = packet.get('msg_size')
        item['is_root'] = packet.get('is_root')
        item['is_broadcast'] = packet.get('is_broadcast')
        
        self.mysql_db.insert_into_db(db, "p2ptest_send_info", item)

        ips = {}
        ips['public_ips'] = packet.get('public_ip')
        self.mysql_db.insert_ingore_into_db(db, "ips_table", ips)

        return True
