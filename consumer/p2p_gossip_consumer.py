#!/usr/bin/env python
#-*- coding:utf8 -*-


import json
import os
import time
import queue
import copy
import threading
from database.p2pbroadcast_sql import BroadcastSql
from common.slogging import slog


class P2PGossipAlarmConsumer(object):
    def __init__(self, q, queue_key_list, alarm_env = 'test'):
        slog.info("p2p_broadcast alarmconsumer init. pid:{0} paraent:{1} queue_key:{2}".format(os.getpid(), os.getppid(), json.dumps(queue_key_list)))

        self.expire_time_  = 20  # 10min, only focus on latest 10 min
        self.consume_step_ = 5  # get_queue return size for one time
        self.alarm_env_ = alarm_env

        # store packet_info from /api/alarm
        self.alarm_queue_ = q
        self.queue_key_list_ = queue_key_list # eg: topargus_alarm_list:0 for one consumer bind to one or more queue_key

        self.msg_send_cache = {}
        self.msg_recv_cache = {}
        self.msg_cache_list = []

        self.msg_info_sql = BroadcastSql()

        self.msg_info_template={
            'uniq_hash':0,
            'msg_hash':0,
            'msg_size':0,
            'send_timestamp':0,
            'src_ip':'',
            'is_root':0,
            'is_broadcast':0,
            'recv_msg_cnt':0,
            'recv_hash_cnt':0,
            'vhost_recv_cnt':0,
            'bypulled_cnt':0,
            'packet_size':0,
            'max_hop':0,
            'avg_hop':0.0,
            'max_delay':0.0,
            'avg_delay':0,
            'hop_num':'',
            'recv_delay':'',
        }

        # demo sql db client
        # self.demo_info_sql_ = DemoInfoSql()

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
            alarm_payload_list = self.alarm_queue_.get_queue_exp(self.queue_key_list_, self.consume_step_)  # return dict or None
            for alarm_payload in alarm_payload_list:
                alarm_type = alarm_payload.get('alarm_type')
                slog.info(alarm_payload)
                if alarm_type == 'p2p_gossip':
                    slog.info(alarm_payload.get('packet'))
                    self.p2p_broadcast_alarm(alarm_payload.get('packet'))
                else:
                    slog.warn('invalid alarm_type:{0}'.format(alarm_type))
        return


    def consume_alarm(self):
        while True:
            slog.info("begin consume_alarm alarm_queue.size is {0}".format(self.alarm_queue_.qsize(self.queue_key_list_)))
            try:
                alarm_payload_list = self.alarm_queue_.get_queue_exp(self.queue_key_list_, self.consume_step_)  # return dict or None
                for alarm_payload in alarm_payload_list:
                    alarm_type = alarm_payload.get('alarm_type')
                    if alarm_type == 'p2p_gossip':
                        self.p2p_broadcast_alarm(alarm_payload.get('packet'))
                    else:
                        slog.warn('invalid alarm_type:{0}'.format(alarm_type))
            except Exception as e:
                slog.warn('catch exception:{0}'.format(e))
        return

    # focus on packet_info(drop_rate,hop_num,timing)
    def p2p_broadcast_alarm(self, packet):
        now = int(time.time() * 1000)
        slog.info(packet)
        '''
        {
            "msg_type": "recv",
            "public_ip": "192.168.50.137",
            "content": {
                "7291557955016184712": {
                    "vhost_recv": 1,
                    "recv_cnt": 0,
                    "recv_hash_cnt": 9,
                    "is_pulled": 0,
                    "hop_num": 3,
                    "packet_size": 3185,
                    "msg_hash": 2430586655,
                    "src_id": "ffffff4d03342538b8001bdda0fbe354000000005cce44724ff771458e68720f5d555515",
                    "dst_id": "ffffff06106b3f851025ad4867a0674700000000bf0b4d5d33927c9b71946f8dc46c1f0a",
                    "timestamp": 1615253902715
                },
                "9845148090015180120": {
                    "vhost_recv": 0,
                    "recv_cnt": 0,
                    "recv_hash_cnt": 1,
                    "is_pulled": 0,
                    "hop_num": 0,
                    "packet_size": 289,
                    "msg_hash": 69805276
                }
            }
        }
        '''

        if packet.get('msg_type') == "recv":
            node_ip = packet.get('public_ip')
            for uniq_hash,msg_recv_detail in packet.get('content').items():
                # print("[DEBUG]", node_ip, uniq_hash)
                # print("[before]",self.msg_recv_cache[uniq_hash][node_ip])
                # print("[add]",msg_recv_detail)

                if uniq_hash not in self.msg_recv_cache:
                    self.msg_recv_cache[uniq_hash]={}
                if node_ip not in self.msg_recv_cache[uniq_hash]:
                    self.msg_recv_cache[uniq_hash][node_ip] = msg_recv_detail
                else:
                    msg_ip_detail = self.msg_recv_cache[uniq_hash][node_ip]
                    # print("[with]",msg_ip_detail)
                    for k,v in msg_recv_detail.items():
                        if k in msg_ip_detail.keys():
                            if k == "timestamp" or k == "hop_num":
                                print("repeated k:",k,msg_recv_detail)
                                msg_ip_detail[k] = min(msg_ip_detail[k], v)
                            else:
                                msg_ip_detail[k] += v
                        else:
                            msg_ip_detail[k] = v
                # if "timestamp" not in self.msg_recv_cache[uniq_hash][node_ip].keys():
                #     self.msg_recv_cache[uniq_hash][node_ip]["timestamp"] = 0
                # print("[end]",self.msg_recv_cache[uniq_hash][node_ip])
                # print("[full hash]", uniq_hash, self.msg_recv_cache[uniq_hash])
        elif packet.get('msg_type') == "send":
            node_ip = packet.get('public_ip')
            for uniq_hash,msg_send_detail in packet.get('content').items():
                if uniq_hash not in self.msg_send_cache:
                    modified_msg_send_info = copy.deepcopy(msg_send_detail)
                    modified_msg_send_info['src_ip'] = node_ip
                    self.msg_send_cache[uniq_hash] = modified_msg_send_info
                    self.msg_cache_list.append(uniq_hash)
                # print("[send]", uniq_hash, self.msg_send_cache[uniq_hash])
                    
                # print(self.msg_send_cache[uniq_hash][node_ip])

        self.dump_db()
        return True


    def dump_db(self):
        # slog.info('ready dump to db')

        now = int(time.time() * 1000)
        # slog.info(len(self.msg_info_cache))
        delete_msg_uniq_hash = []

        '''
{'timestamp': 1615257666069, 'msg_size': 100, 'src_id': 'ffffff253291105849d19b2605215fc4000000007e8c304e8993efb0f2b59b962849e73a', 'dst_id': 'ffffff7f7fffffffffffffffffffffff000000004a5b79fe5531e300fd5df39a59f5ffef'}
{'vhost_recv': 1, 'recv_cnt': 2, 'recv_hash_cnt': 3, 'is_pulled': 0, 'hop_num': 1, 'packet_size': 2051, 'msg_hash': 1551666620, 'src_id': 'ffffff253291105849d19b2605215fc4000000007e8c304e8993efb0f2b59b962849e73a', 'dst_id': 'ffffff2f6318e7b803a58f40d66da75300000000b8bee023b89fbb95b4792755473db52a', 'timestamp': 1615257660064}

{'timestamp': 1615258192085, 'msg_size': 100, 'src_id': 'ffffff253291105849d19b2605215fc4000000007e8c304e8993efb0f2b59b962849e73a', 'dst_id': 'ffffff7f7fffffffffffffffffffffff000000004a5b79fe5531e300fd5df39a59f5ffef', 'src_ip': '192.168.50.136'}
{'192.168.50.146': {'vhost_recv': 0, 'recv_cnt': 0, 'recv_hash_cnt': 1, 'is_pulled': 0, 'hop_num': 0, 'packet_size': 310, 'msg_hash': 2349411006}, '192.168.50.140': {'vhost_recv': 0, 'recv_cnt': 0, 'recv_hash_cnt': 1, 'is_pulled': 0, 'hop_num': 0, 'packet_size': 316, 'msg_hash': 2349411006}, '192.168.50.138': {'vhost_recv': 0, 'recv_cnt': 1, 'recv_hash_cnt': 0, 'is_pulled': 0, 'hop_num': 0, 'packet_size': 364, 'msg_hash': 2349411006}, '192.168.50.141': {'vhost_recv': 0, 'recv_cnt': 1, 'recv_hash_cnt': 0, 'is_pulled': 0, 'hop_num': 0, 'packet_size': 355, 'msg_hash': 2349411006}, '192.168.50.135': {'vhost_recv': 0, 'recv_cnt': 1, 'recv_hash_cnt': 0, 'is_pulled': 0, 'hop_num': 0, 'packet_size': 378, 'msg_hash': 2349411006}}
        '''


        for uniq_hash in self.msg_cache_list:
            # slog.info("dump hash: {0}".format(uniq_hash))
            timestamp = int(self.msg_send_cache[uniq_hash]['timestamp'])
            if now - timestamp > 120 * 1000:
                if uniq_hash not in self.msg_recv_cache:
                    # print(timestamp)
                    continue

                # print(uniq_hash)
                msg_recv_info = self.msg_recv_cache[uniq_hash]
                # print(msg_recv_info)
                msg_send_info = self.msg_send_cache[uniq_hash]
                # print(msg_send_info)

                # for each_recv_info in msg_recv_info.values():
                    # if "timestamp" not in each_recv_info.keys():
                        # print("lack timestamp:",each_recv_info)
                        # continue
                        # each_recv_info["timestamp"] = now
                # for each_recv_info in msg_recv_info.values():
                    # if "hop_num" not in each_recv_info.keys():
                        # print("lack hop_num:",each_recv_info)
                        # continue
                        # each_recv_info["hop_num"] = 0

                msg_info_val = copy.deepcopy(self.msg_info_template)

                msg_info_val["uniq_hash"] = uniq_hash
                msg_info_val["msg_hash"] = msg_send_info['msg_hash']
                msg_info_val["msg_size"] = int(msg_send_info['msg_size'])
                msg_info_val["send_timestamp"] = timestamp
                msg_info_val["src_ip"] = msg_send_info["src_ip"]
                msg_info_val["is_root"] = msg_send_info["is_root"]
                msg_info_val["is_broadcast"] = msg_send_info["is_broadcast"]
                msg_info_val["recv_msg_cnt"] = sum([
                    each_recv_info["recv_cnt"]
                    for each_recv_info in msg_recv_info.values()
                ])
                msg_info_val["recv_hash_cnt"] = sum([
                    each_recv_info["recv_hash_cnt"]
                    for each_recv_info in msg_recv_info.values()
                ])
                msg_info_val["vhost_recv_cnt"] = sum([
                    each_recv_info["vhost_recv"]
                    for each_recv_info in msg_recv_info.values()
                ])
                msg_info_val["bypulled_cnt"] = sum([
                    each_recv_info["is_pulled"]
                    for each_recv_info in msg_recv_info.values()
                ])
                msg_info_val["packet_size"] = sum([
                    each_recv_info["packet_size"]
                    for each_recv_info in msg_recv_info.values()
                ])
                hop_list = [each_recv_info["hop_num"]
                            for each_recv_info in msg_recv_info.values() if "hop_num" in each_recv_info]
                print("hop_list: ", len(hop_list), hop_list)
                max_hop = 9999 if not len(hop_list) else max(hop_list, key=abs)
                avg_hop = 9999 if not len(hop_list) else round(sum(hop_list) / len(hop_list), 1)
                msg_info_val['max_hop'] = max_hop
                msg_info_val['avg_hop'] = avg_hop

                delay_list = [(int(each_recv_info["timestamp"]) - timestamp)
                              for each_recv_info in msg_recv_info.values() if "timestamp" in each_recv_info]
                print("delay_list", len(delay_list), delay_list)
                max_delay = 9999 if not len(delay_list) else max(delay_list, key=abs)
                avg_delay = 9999 if not len(delay_list) else round(sum(delay_list) / len(delay_list), 1)
                msg_info_val['max_delay'] = max_delay
                msg_info_val['avg_delay'] = avg_delay

                hop_num_dict = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0,
                                5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0}
                for hop_ in [
                        each_recv_info["hop_num"]
                        for each_recv_info in msg_recv_info.values() if "hop_num" in each_recv_info
                ]:
                    hop_num_dict[min(10, (hop_))] += 1
                msg_info_val['hop_num'] = str(hop_num_dict)

                delay_dict = {-1: 0, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0,
                              6: 0, 7: 0, 8: 0, 9: 0, 10: 0}  # 0 : 0-50 delay;  1: 50-100ms delay
                for recv_time in [
                        each_recv_info["timestamp"]
                        for each_recv_info in msg_recv_info.values() if "timestamp" in each_recv_info
                ]:
                    delay_dict[min(10, (max(-1, (recv_time - timestamp))) //
                                   (50 * 1000))] += 1
                msg_info_val['recv_delay'] = str(delay_dict)

                print("[msg_info_val]:", msg_info_val)
                delete_msg_uniq_hash.append(uniq_hash)
                self.msg_info_sql.insert_to_db(msg_info_val)
        
        for _hash in delete_msg_uniq_hash:
            del self.msg_send_cache[_hash]
            if _hash in self.msg_recv_cache:
                del self.msg_recv_cache[_hash]
            self.msg_cache_list.remove(_hash)

        #         '''
        #         msg_info_val = copy.deepcopy(self.msg_info_template)

        #         msg_info_val["uniq_hash"] = uniq_hash
        #         msg_info_val["msg_hash"] = [i for i in msg_recv_info.values()][0]["msg_hash"]
        #         msg_info_val["msg_size"] = [i for i in msg_recv_info.values()][0]["msg_size"]
        #         msg_info_val["send_timestamp"] = timestamp
        #         msg_info_val["src_ip"] = self.msg_send_cache[uniq_hash]["src_ip"]
        #         msg_info_val["recv_nodes_num"] = len(msg_recv_info)
        #         msg_info_val["recv_nodes_cnt"] = sum([
        #             each_recv_info["recv_cnt"]
        #             for each_recv_info in msg_recv_info.values()
        #         ])
        #         msg_info_val["vhost_recv_cnt"] = sum([
        #             each_recv_info["vhost_recv"]
        #             for each_recv_info in msg_recv_info.values()
        #         ])

        #         hop_num_dict = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0} # 0: 0-5 hop
        #         for hop_ in [
        #                 each_recv_info["hop_num"]
        #                 for each_recv_info in msg_recv_info.values()
        #         ]:
        #             hop_num_dict[min(4, (hop_ // 5))] += 1
        #         msg_info_val['hop_num'] = str(hop_num_dict)

        #         delay_dict = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0} # 0 : 0-200ms delay;  1: 200-400ms delay
        #         for recv_time in [
        #                 each_recv_info["timestamp"]
        #                 for each_recv_info in msg_recv_info.values()
        #         ]:
        #             delay_dict[min(4, (recv_time - timestamp) //
        #                            (200 * 1000))] += 1
        #         msg_info_val['recv_delay'] = str(delay_dict)
        #         msg_info_val['broadcast'] = self.msg_send_cache[uniq_hash][
        #             "is_broadcast"]
        #         '''
        #         {
        #             'uniq_hash': '5393531474291252347', 
        #             'msg_hash': 1692545279, 
        #             'msg_size': 100, 
        #             'send_timestamp': 1612404476564517, 
        #             'src_ip': '192.168.50.136', 
        #             'recv_nodes_num': 2, 
        #             'recv_nodes_cnt': 15, 
        #             'vhost_recv_cnt': 2, 
        #             'hop_num': '{0: 2, 1: 0, 2: 0, 3: 0, 4: 0}', 
        #             'recv_delay': '{0: 1, 1: 1, 2: 0, 3: 0, 4: 0}', 
        #             'broadcast': 1
        #         }
        #         '''
        #         self.msg_info_sql.insert_to_db(msg_info_val)
        #         # print("sql: {0}".format(msg_info_val))

        #         # del self.msg_send_cache[uniq_hash]
        #         # del self.msg_recv_cache[uniq_hash]
        #         delete_msg_uniq_hash.append(uniq_hash)
        #     else:
        #         break

        # for _hash in delete_msg_uniq_hash:
        #     del self.msg_send_cache[_hash]
        #     if _hash in self.msg_recv_cache:
        #         del self.msg_recv_cache[_hash]
        #     self.msg_cache_list.remove(_hash)
        #     '''
        # for msg_uniq_hash, msg_info_val in self.msg_info_cache.items():
        #     # slog.info("{0}".format(msg_info_val["send_timestamp"]))
        #     if msg_info_val["send_timestamp"] > 0 and (now - msg_info_val["send_timestamp"] > 15 * 1000 * 1000):
        #         # slog.info("log in db: {0}".format(msg_info_val))
        #         del msg_info_val["latest_update_time"]
        #         msg_info_val["recv_nodes_cnt"] -= msg_info_val["vhost_recv_cnt"]
        #         self.msg_info_sql.insert_to_db(msg_info_val)
        #         delete_msg_uniq_hash.append(msg_uniq_hash)
        #         continue
        #     # slog.info("{0} {1}".format(now, msg_info_val))
        # # self.demo_info_sql_.update_insert_to_db()
        # for _hash in delete_msg_uniq_hash:
        #     del self.msg_info_cache[_hash]
        # return
