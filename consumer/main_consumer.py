#!/usr/bin/env python
#-*- coding:utf8 -*-

import sys
import json
import argparse

import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
log_path = os.path.join(project_path, "log/topargus-consumer.log")
os.environ['LOG_PATH'] =  log_path
import common.slogging as slogging
from common.slogging import slog

import common.my_queue as my_queue
import common.config as sconfig
from multiprocessing import Process
# import p2p_gossip_consumer
from consumer import metrics_timer_consumer
from consumer import metrics_flow_consumer
from consumer import metrics_counter_consumer


mq = my_queue.RedisQueue(host= sconfig.REDIS_HOST, port=sconfig.REDIS_PORT, password=sconfig.REDIS_PASS)

def run(alarm_type, alarm_env = 'test'):
    global mq
    all_queue_key = mq.get_all_queue_keys()  # set of queue_key
    qkey_map = {
            'p2p_gossip': [],
            'metrics_timer':[],
            'metrics_flow':[],
            'metrics_counter':[],
            }
    for qkey in all_queue_key:
        if qkey.find('p2p_gossip') != -1:
            qkey_map['p2p_gossip'].append(qkey)
        if qkey.find('metrics_timer')!=-1:
            qkey_map['metrics_timer'].append(qkey)
        if qkey.find('metrics_flow')!=-1:
            qkey_map['metrics_flow'].append(qkey)
        if qkey.find('metrics_counter')!=-1:
            qkey_map['metrics_counter'].append(qkey)

    slog.warn('qkey_map:{0}'.format(json.dumps(qkey_map)))

    consumer_list = []

    # if alarm_type == 'p2p_gossip':
    #     for qkey in qkey_map.get('p2p_gossip'):
    #         slog.warn(
    #             'create consumer for p2p_gossip, assign queue_key:{0}'.format(qkey))
    #         consumer = p2p_gossip_consumer.P2PGossipAlarmConsumer(
    #             q=mq, queue_key_list=[qkey], alarm_env=alarm_env)
    #         consumer_list.append(consumer)

    if alarm_type == 'test':
        for qkey in qkey_map.get('metrics_timer'):
            consumer = metrics_timer_consumer.MetricsTimerConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('metrics_flow'):
            consumer = metrics_flow_consumer.MetricsFlowConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('metrics_counter'):
            consumer = metrics_counter_consumer.MetricsCounterConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)


    if not consumer_list:
        slog.warn("no consumer created")
        return

    print(consumer_list)

    process_list = []
    for c in consumer_list:
        p = Process(target=c.run)
        process_list.append(p)

    slog.warn('{0} consumer started, ==== start'.format(len(consumer_list)))

    for p in process_list:
        p.start()

    for p in process_list:
        p.join()

    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.description='TOP-Argus consumer，多进程方式启动一个消费者，绑定到某个类型的报警内容，进行消费'
    parser.add_argument('-t', '--type', help='bind with alarm_type,eg: packet, networksize...', default = '')
    parser.add_argument('-e', '--env', help='env, eg: test,docker', default = 'test')
    args = parser.parse_args()

    if not args.type:
        slog.warn("please give one type or 'all'")
        sys.exit(-1)

    alarm_type = args.type
    alarm_env = args.env
    print('type:{0} env:{1}'.format(alarm_type,alarm_env))
    slogging.start_log_monitor()
    run(alarm_type, alarm_env)
