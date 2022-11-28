#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class VnodeStatusConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("VnodeStatusConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.vnode_status_template = {
            "timestamp": 0,
            "public_ip": "",
            "rec":0,
            "zec":0,
            "auditor":0,
            "validator":0,
            "archive":0,
            "edge":0,
            "fullnode":0,
            "evm_auditor":0,
            "evm_validator":0,
            "relay":0,
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
                if alarm_type == 'vnode_status':
                    # slog.info(alarm_payload.get('packet'))
                    self.vnode_status_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'vnode_status':
                        self.vnode_status_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def vnode_status_handle(self, packet):
        # slog.info(packet)
        '''
        {
            "alarm_type": "vnode_status",
            "packet": {
                "timestamp": 1625108040,
                "env": "test_database_name",
                "public_ip": "192.168.181.128",
                "rec": 6,
                "zec": 0,
                "auditor": 4,
                "validator": 0,
                "archive": 2,
                "edge": 1
            }
        }
        '''
        db = packet.get('env')
        item = copy.deepcopy(self.vnode_status_template)
        item['timestamp'] = packet.get('timestamp')
        item['public_ip'] = packet.get('public_ip')
        item['rec'] = packet.get('rec')
        item['zec'] = packet.get('zec')
        item['auditor'] = packet.get('auditor')
        item['validator'] = packet.get('validator')
        item['archive'] = packet.get('archive')
        item['edge'] = packet.get('edge')
        if packet.get('fullnode'):
            item['fullnode'] = packet.get('fullnode')
        if packet.get('evm_auditor'):
            item['evm_auditor'] = packet.get('evm_auditor')
        if packet.get('evm_validator'):
            item['evm_validator'] = packet.get('evm_validator')
        if packet.get('relay'):
            item['relay'] = packet.get('relay')
        
        self.mysql_db.insert_into_db(db, "vnode_status", item)

        ips = {}
        ips['public_ips'] = packet.get('public_ip')
        self.mysql_db.insert_ingore_into_db(db, "ips_table", ips)

        return True
