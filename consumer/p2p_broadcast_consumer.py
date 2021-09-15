#!/usr/bin/env python
# -*- coding:utf8 -*-


import json
import os
import time
import copy
from database.dispatch import MultiDB
from common.slogging import slog


class P2pBroadcastConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env='test'):
        slog.info("P2pBroadcastConsumer init. pid:{0} paraent:{1} queue_key:{2}".format(
            os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.alarm_env_ = alarm_env
        self.consume_step_ = 30

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key
        self.queue_key_list_ = queue_key_list

        self.mysql_db = MultiDB()
        self.msg_cache = {}
        self.last_dump_checktime = int(time.time())
        self.msg_template = {
            'src_node_id': '',
            'dst_node_id': '',
            'src_ip' : '',
            'env': '',
            'msg_hash': 0,
            'msg_size': 0,
            'is_root':0,
            'is_broadcast':0,
            'send_timestamp':0,
            'recv_info' : {} # ip:msg_recv_info_template
        }
        self.msg_recv_info_template = {
            'src_node_id': '',
            'dst_node_id': '',
            'recv_timestamp': 0,
            'public_ip': '',
            'recv_packet_size': 0,
            'hop_num': 0,
        }
        self.cache_num = 100
        self.raw_msg_info_cache = {

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
                if alarm_type == 'p2pbroadcast':
                    slog.info(alarm_payload.get('packet'))
                    self.p2pbroadcast_handle(alarm_payload.get('packet'))
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
                    if alarm_type == 'p2pbroadcast':
                        self.p2pbroadcast_handle(
                            alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    def p2pbroadcast_handle(self, packet):
        slog.info(packet)
        '''
        {
            "alarm_type": "p2pbroadcast",
            "packet": {
                "type": "recv",
                "src_node_id": "f60000ff020003ff.0200000000000004",
                "dst_node_id": "f60000ff020003ff.0200000000000004",
                "hop_num": 2,
                "msg_hash": 787117631,
                "msg_size": 555,
                "is_root": 0,
                "is_broadcast": 1,
                "packet_size": 736,
                "timestamp": 1626068690853,
                "public_ip": "192.168.181.128/tmp/rec1/xtop.log",
                "env": "local_diff"
            }
        }
        {
            "alarm_type": "p2pbroadcast",
            "packet": {
                "type": "send",
                "src_node_id": "f60000ff020003ff.0200000000000004",
                "dst_node_id": "f60000ff020003ff.0200000000000004",
                "hop_num": 0,
                "msg_hash": 1235517471,
                "msg_size": 555,
                "is_root": 0,
                "is_broadcast": 1,
                "timestamp": 1626068620757,
                "public_ip": "192.168.181.128/tmp/rec1/xtop.log",
                "env": "local_diff"
            }
        }
        p2pbroadcast_template = {
            # by type: send
            'src_node_id': 'xxx',
            'dst_node_id': 'xxx',
            'msg_hash': 123,
            'msg_size': 123,
            'is_root':1,
            'is_broadcast':1,
            'send_timestamp':123456,
            
            # by type recv
            'recv_info' : [
                {
                    'src_node_id': 'xxx',
                    'dst_node_id': 'xxx',
                    'recv_timestamp':1234,
                    'public_ip':'123.123.123.123',
                    'recv_packet_size':1234,
                    'hop_num':1,
                },
            ]
        }
        '''
        db = packet.get('env')
        msg_hash = packet.get('msg_hash')
        msg_type = packet.get('type')
        public_ip = packet.get('public_ip')
        if msg_hash not in self.msg_cache:
            self.msg_cache[msg_hash] = copy.deepcopy(self.msg_template)
        t_msg_cache = self.msg_cache[msg_hash]

        if msg_type == 'send':
            t_msg_cache['src_node_id'] = packet.get('src_node_id')
            t_msg_cache['dst_node_id'] = packet.get('dst_node_id')
            t_msg_cache['src_ip'] = public_ip
            t_msg_cache['env'] = db
            t_msg_cache['msg_hash'] = packet.get('msg_hash')
            t_msg_cache['msg_size'] = packet.get('msg_size')
            t_msg_cache['is_root'] = packet.get('is_root')
            t_msg_cache['is_broadcast'] = packet.get('is_broadcast')
            t_msg_cache['send_timestamp'] = packet.get('timestamp')
        elif msg_type == 'recv':
            if public_ip not in t_msg_cache['recv_info']:
                t_msg_cache['recv_info'][public_ip] = copy.deepcopy(self.msg_recv_info_template)
            t_msg_recv_info = t_msg_cache['recv_info'][public_ip]
            t_msg_recv_info['src_node_id'] = packet.get('src_node_id')
            t_msg_recv_info['dst_node_id'] = packet.get('dst_node_id')
            t_msg_recv_info['recv_timestamp'] = packet.get('timestamp')
            t_msg_recv_info['public_ip'] = packet.get('public_ip')
            t_msg_recv_info['recv_packet_size'] = packet.get('packet_size')
            t_msg_recv_info['hop_num'] = packet.get('hop_num')
        else:
            slog.info('unknown type msg {0}'.format(packet))

        raw_msg_info = {
            'public_ip': packet.get('public_ip'),
            'msg_hash': packet.get('msg_hash'),
            'timestamp': packet.get('timestamp'),
            'type': packet.get('type'),
            'src_node_id': packet.get('src_node_id'),
            'dst_node_id': packet.get('dst_node_id'),
            'hop_num': packet.get('hop_num'),
            'msg_size': packet.get('msg_size'),
            'is_root': packet.get('is_root'),
            'is_broadcast': packet.get('is_broadcast'),
        }

        if db not in self.raw_msg_info_cache:
            self.raw_msg_info_cache[db] = []
        self.raw_msg_info_cache[db].append(raw_msg_info)
        if len(self.raw_msg_info_cache[db]) > self.cache_num:
            self.mysql_db.multi_insert_into_db(db,"p2p_raw_msg_info",self.raw_msg_info_cache[db])
            self.raw_msg_info_cache[db] = []
        # self.mysql_db.insert_into_db(db, 'p2p_raw_msg_info', raw_msg_info)

        if int(time.time()) - self.last_dump_checktime > 10:
            self.try_dump_cache_to_db()
            self.last_dump_checktime = int(time.time())

        return True
    
    def try_dump_cache_to_db(self):
        now_time = int(time.time()*1000)
        remove_msg_hash = []
        for _hash,_t_msg_cache in self.msg_cache.items():
            st = _t_msg_cache['send_timestamp']
            if st == 0: continue
            if now_time - st > 120*1000:
                remove_msg_hash.append(_hash)
                msg_info = {
                    'send_timestamp':_t_msg_cache['send_timestamp'],
                    'msg_hash':_t_msg_cache['msg_hash'],
                    'src_node_id':_t_msg_cache['src_node_id'],
                    'dst_node_id':_t_msg_cache['dst_node_id'],
                    'src_ip':_t_msg_cache['src_ip'],
                    'msg_size':_t_msg_cache['msg_size'],
                    'is_root':_t_msg_cache['is_root'],
                    'is_broadcast':_t_msg_cache['is_broadcast'],
                    'recv_node_cnt' : len(_t_msg_cache['recv_info']),
                    'recv_avg_delay': sum([each_recv_info['recv_timestamp'] - _t_msg_cache['send_timestamp'] for each_recv_info in _t_msg_cache['recv_info'].values()])/len(_t_msg_cache['recv_info']) if len(_t_msg_cache['recv_info']) else 0.0,
                    'avg_hop_num': sum([each_recv_info['hop_num'] for each_recv_info in _t_msg_cache['recv_info'].values()])/len(_t_msg_cache['recv_info']) if len(_t_msg_cache['recv_info']) else 0.0,
                    'avg_packet_size': sum([each_recv_info['recv_packet_size'] for each_recv_info in _t_msg_cache['recv_info'].values()])/len(_t_msg_cache['recv_info']) if len(_t_msg_cache['recv_info']) else 0.0,
                }
                self.mysql_db.insert_into_db(_t_msg_cache['env'],'p2p_dump_msg_info',msg_info)
        
        for _hash in remove_msg_hash:
            del self.msg_cache[_hash]
        return

        
