#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class P2pKadinfoConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("P2pKadinfoConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 3

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.kadinfo_root_template = {
            "public_ip": "",
            "node_id": "",

            "neighbours": 0,
            "last_update_time": 0,
        }
        self.kadinfo_elect_template = {
            "public_ip": "",
            "node_id": "",
            "service_type":"",
            "node_size": 0,
            "height": 0,

            "unknown_node_size": 0,
            "last_update_time": 0,
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
                if alarm_type == 'kadinfo':
                    # slog.info(alarm_payload.get('packet'))
                    self.kadinfo_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'kadinfo':
                        self.kadinfo_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def kadinfo_handle(self, packet):
        # slog.info(packet)
        '''
        {
            "alarm_type": "kadinfo",
            "packet": {
                "service_type": "zec",
                "height": 3,
                "node_size": 8,
                "unknown_node_size": 0,
                "local_nodeid": "f60000ff02000005.0200000000000003",
                "update_time": "xxx",
                "public_ip": "192.168.181.128/tmp/rec3/xtop.log",
                "env": "local_diff"
            }
        }
        {
            "alarm_type": "kadinfo",
            "packet": {
                "service_type": "root",
                "neighbours": 13,
                "local_nodeid": "846fffff039da3ac.3974af7af9f7f8c0",
                "update_time": "xxx",
                "public_ip": "192.168.181.128/tmp/rec3/xtop.log",
                "env": "local_diff"
            }
        }
        '''
        db = packet.get('env')
        if packet.get('service_type') == 'root':
            item = copy.deepcopy(self.kadinfo_root_template)
            item['public_ip'] = packet.get('public_ip')
            item['node_id'] = packet.get('local_nodeid')
            item['neighbours'] = packet.get('neighbours')
            item['last_update_time'] = packet.get('update_time')
            update_list = ['neighbours','last_update_time']
            self.mysql_db.insert_update_into_db(db, "kadinfo_root", item, update_list)
        else:
            item = copy.deepcopy(self.kadinfo_elect_template)
            item['public_ip'] = packet.get('public_ip')
            item['node_id'] = packet.get('local_nodeid')
            item['service_type'] = packet.get('service_type')
            item['node_size'] = packet.get('node_size')
            item['height'] = packet.get('height')
            item['unknown_node_size'] = packet.get('unknown_node_size')
            item['last_update_time'] = packet.get('update_time')
            update_list = ['unknown_node_size','last_update_time']
            self.mysql_db.insert_update_into_db(db, "kadinfo_elect", item, update_list)
        

        return True
