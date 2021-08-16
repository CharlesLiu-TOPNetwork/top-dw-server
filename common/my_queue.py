#!/usr/bin/env python
#-*- coding:utf8 -*-

import redis
import json
import random
from common.slogging import slog

class RedisQueue(object):
    def __init__(self, host, port, password):
        self.mypool  = redis.ConnectionPool(host = host, port = port, password = password, decode_responses=True)
        self.myredis = redis.StrictRedis(connection_pool = self.mypool)
        self.all_queue_keys = 'topargus_alarm_allkey_set'
        self.queue_key_base = 'topargus_alarm_list'
        self.alarm_type_queue_num = 4   # every type has 4 queue
        self.all_queue_keys_set = set()  # keep all queue_key in cache

        # add already known type
        # for i in range(0, self.alarm_type_queue_num):
        #     qkey_perf = '{0}:p2p_gossip:{1}'.format(self.queue_key_base,i)
        #     self.myredis.sadd(self.all_queue_keys,qkey_perf)
        #     self.all_queue_keys_set.add(qkey_perf)

        # for i in range(0, self.alarm_type_queue_num):
        #     qkey_perf = '{0}:metrics_timer:{1}'.format(self.queue_key_base,i)
        #     self.myredis.sadd(self.all_queue_keys,qkey_perf)
        #     self.all_queue_keys_set.add(qkey_perf)
        # for i in range(0, self.alarm_type_queue_num):
        #     qkey_perf = '{0}:metrics_flow:{1}'.format(self.queue_key_base,i)
        #     self.myredis.sadd(self.all_queue_keys,qkey_perf)
        #     self.all_queue_keys_set.add(qkey_perf)
        # for i in range(0, self.alarm_type_queue_num):
        #     qkey_perf = '{0}:metrics_counter:{1}'.format(self.queue_key_base,i)
        #     self.myredis.sadd(self.all_queue_keys,qkey_perf)
        #     self.all_queue_keys_set.add(qkey_perf)

        # metrics_timer
        qkey_perf = '{0}:metrics_timer'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)
        
        # metrics_flow
        qkey_perf = '{0}:metrics_flow'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)
        
        # metrics_counter
        qkey_perf = '{0}:metrics_counter'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # vnode_status
        qkey_perf = '{0}:vnode_status'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # xsync_interval
        qkey_perf = '{0}:xsync_interval'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # kadinfo
        qkey_perf = '{0}:kadinfo'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # p2pbroadcast
        qkey_perf = '{0}:p2pbroadcast'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # txpool
        qkey_perf = '{0}:txpool_state'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)
        qkey_perf = '{0}:txpool_receipt'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)
        qkey_perf = '{0}:txpool_cache'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # metrics_alarm
        qkey_perf = '{0}:metrics_alarm'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)

        # metrics_array_counter
        qkey_perf = '{0}:metrics_array_counter'.format(self.queue_key_base)
        self.myredis.sadd(self.all_queue_keys,qkey_perf)
        self.all_queue_keys_set.add(qkey_perf)


        return
    
    def get_all_queue_keys(self):
        ret = self.myredis.smembers(self.all_queue_keys)
        return list(ret)

    def get_queue_key_of_alarm(self, alarm_item):
        # attention: using right field as hash value, will reduce progress communication
        alarm_type = alarm_item.get('alarm_type')
        msg_hash = None
        if alarm_type == 'p2p_gossip':
            msg_hash = int(list(alarm_item.get('packet').get('content').keys())[0]) 
        else:
            return '{0}:{1}'.format(self.queue_key_base,alarm_type)
        '''
        elif alarm_type in ['vnode_status','xsync_interval','kadinfo','p2pbroadcast','txpool_state','txpool_receipt','txpool_cache','metrics_alarm','metrics_array_counter'] :
            return '{0}:{1}'.format(self.queue_key_base,alarm_type)
        else:
            msg_hash = random.randint(0,10000)

        index = msg_hash % self.alarm_type_queue_num   # 0,1,2,3
        qkey = '{0}:{1}:{2}'.format(self.queue_key_base, alarm_type, index)
        if qkey not in self.all_queue_keys_set:
            self.myredis.sadd(self.all_queue_keys, qkey)
            self.all_queue_keys_set.add(qkey)

        # slog.debug('get qkey:{0}'.format(qkey))
        return qkey 
        '''

    def qsize(self, queue_key_list):
        if not queue_key_list:
            return 0
        # always return the first list (high level priority)
        return self.myredis.llen(queue_key_list[0])

    # handle alarm 
    def handle_alarm(self, data):
        if not data:
            return
    
        for item in data:
            self.put_queue(item)
        return
    
    def handle_alarm_env_ip(self,data,env,ip):
        if not data:
            return
        # print(env,ip)
        # print(data)
        for _each_alarm in data:
            # print(_each_alarm)
            _each_alarm['packet']['public_ip'] = ip
            _each_alarm['packet']['env'] = env
            self.put_queue(_each_alarm)
        # print("[after]:",data)
        return


    def put_queue(self, item):
        if not isinstance(item, dict):
            return

        qkey = self.get_queue_key_of_alarm(item)
        # item is dict, serialize to str
        # TODO(smaug)
        size = self.qsize([qkey])
        if size >= 1000000:
            slog.warn("queue_key:{0} size {1} beyond 1000000".format(qkey, size))
            return
        self.myredis.lpush(qkey, json.dumps(item))
        slog.debug("put_queue alarm:{0} in queue {1}, now size is {2}".format(json.dumps(item), qkey, self.qsize([qkey])))
        return

    def get_queue(self, queue_key_list):
        item = self.myredis.brpop(queue_key_list, timeout=0) # will block here if no data get, return item is tuple
        if not item:
            return None
        slog.debug('get_queue {0}'.format(item))
        return json.loads(item[1])
    
    # get multi-item one time
    def get_queue_exp(self, queue_key_list, step = 50):
        item_list = []
        for i in range(0, step):
            item = self.get_queue(queue_key_list)
            if item != None:
                item_list.append(item)
        slog.debug('get_queue multi-item size:{0}'.format(len(item_list)))
        return item_list


# class TopArgusRedis(object):
#     def __init__(self, host, port, password):
#         self.host_      = host
#         self.port_      = port
#         self.password_  = password
#         self.myredis_     = None
#         return

#     def connect(self):
#         try:
#             mypool  = redis.ConnectionPool(host = self.host_, port = self.port_, password = self.password_, decode_responses=True)
#             self.myredis_ = redis.StrictRedis(connection_pool = mypool)
#         except Exception as e:
#             slog.warn('connect redis host:{0} port:{1} failed'.format(self.host_, self.port_))
#             self.myredis_ = None
#         finally:
#             return self.myredis_
