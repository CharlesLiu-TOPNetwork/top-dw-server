#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class TxpoolCacheConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("TxpoolCacheConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.txpool_cache_template = {
            "send_timestamp": 0,
            "send_cur": 0,
            "recv_cur": 0,
            "confirm_cur": 0,
            "unconfirm_cur": 0,
            "push_send_fail": 0,
            "push_receipt_fail": 0,
            "duplicate_cache": 0,
            "repeat_cache": 0,
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
                if alarm_type == 'txpool_cache':
                    slog.info(alarm_payload.get('packet'))
                    self.txpool_cache_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'txpool_cache':
                        self.txpool_cache_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def txpool_cache_handle(self, packet):
        slog.info(packet)
        '''
        {
            "alarm_type": "txpool_cache",
            "packet": {
                "send_cur": 0,
                "recv_cur": 0,
                "confirm_cur": 0,
                "unconfirm_cur": 0,
                "push_send_fail": 0,
                "push_receipt_fail": 0,
                "duplicate": 0,
                "repeat": 0,
                "send_timestamp": 1627442400
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.txpool_cache_template)
        item['send_timestamp'] = packet.get('send_timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['send_cur'] = packet.get('send_cur')
        item['recv_cur'] = packet.get('recv_cur')
        item['confirm_cur'] = packet.get('confirm_cur')
        item['unconfirm_cur'] = packet.get('unconfirm_cur')
        item['push_send_fail'] = packet.get('push_send_fail')
        item['push_receipt_fail'] = packet.get('push_receipt_fail')
        item['duplicate_cache'] = packet.get('duplicate')
        item['repeat_cache'] = packet.get('repeat')
        
        
        self.mysql_db.insert_into_db(db, "txpool_cache", item)

    
        return True
