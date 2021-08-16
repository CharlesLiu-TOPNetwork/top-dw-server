#!/usr/bin/env python
#-*- coding:utf8 -*-

import sys
import json
import random
import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
log_path = os.path.join(project_path, "log/topargus-proxy.log")
os.environ['LOG_PATH'] =  log_path
from common.slogging import slog
import common.slogging as slogging
import common.my_queue as my_queue
import common.config as sconfig


import redis

mypool  = redis.ConnectionPool(host = sconfig.REDIS_HOST, port = sconfig.REDIS_PORT, password = sconfig.REDIS_PASS, decode_responses=True)
myredis = redis.StrictRedis(connection_pool = mypool)

def put_queue(qkey, item):
    if not isinstance(item, dict):
        return
    myredis.lpush(qkey, json.dumps(item))
    return

def random_str():
    return ''.join(random.sample('abcd',3))

def random_value():
    return random.randint(1,10000)

def generate_rand_data_into_redis():
    data = [
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}},
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}},
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}, 
        {"alarm_type": "metrics_counter", "packet": {"send_timestamp": 1629092400, "category": random_str(), "tag": random_str(), "count": random_value(), "value": random_value()}}
        ]
    for _each_alarm in data:
        # print(_each_alarm)
        _each_alarm['packet']['public_ip'] = 'test_ip'
        _each_alarm['packet']['env'] = 'test_perf_20210816'
        put_queue('topargus_alarm_list:metrics_counter:2', _each_alarm)
    return

def run():
    for _ in range(10000):
        generate_rand_data_into_redis()
    return


if __name__ == '__main__':
    run()


