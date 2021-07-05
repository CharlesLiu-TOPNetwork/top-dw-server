#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class XsyncIntervalConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("XsyncIntervalConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.xsync_interval_template = {
            "table_address": "",
            "sync_mod": "",
            "send_timestamp": 0,
            "public_ip": "",
            "self_min": 0,
            "self_max": 0,
            "peer_min": 0,
            "peer_max": 0,
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
                if alarm_type == 'xsync_interval':
                    slog.info(alarm_payload.get('packet'))
                    self.xsync_interval_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'xsync_interval':
                        self.xsync_interval_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def xsync_interval_handle(self, packet):
        slog.info(packet)
        '''
        {"alarm_type": "xsync_interval",
            "packet": {
                "env": "test_database_name",
                "public_ip": "192.168.181.128",
                "sync_mod": "full",
                "table_address": "Ta0000gRD2qVpp2S7UpjAsznRiRhbE1qNnhMbEDp@192",
                "send_timestamp": 1625222100,
                "self_min": 0,
                "self_max": 0,
                "peer_min": 0,
                "peer_max": 0
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.xsync_interval_template)

        item['table_address'] = packet.get('table_address')
        item['sync_mod'] = packet.get('sync_mod')
        item['send_timestamp'] = packet.get('send_timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['self_min'] = packet.get('self_min')
        item['self_max'] = packet.get('self_max')
        item['peer_min'] = packet.get('peer_min')
        item['peer_max'] = packet.get('peer_max')
        
        self.mysql_db.insert_into_db(db, "xsync_interval", item)

        return True
