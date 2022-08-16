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
from consumer import vnode_status_consumer
from consumer import xsync_interval_consumer
from consumer import p2p_kadinfo_consumer
from consumer import p2p_broadcast_consumer
from consumer import txpool_state_consumer
from consumer import txpool_receipt_consumer
from consumer import txpool_cache_consumer
from consumer import metrics_alarm_consumer
from consumer import metrics_array_counter_consumer
from consumer import p2ptest_sendrecord_consumer
from consumer import p2ptest_send_consumer
from consumer import p2ptest_recv_consumer
from consumer import relayer_gas_consumer

mq = my_queue.RedisQueue(host= sconfig.REDIS_HOST, port=sconfig.REDIS_PORT, password=sconfig.REDIS_PASS)

def run(alarm_type, alarm_env = 'test'):
    global mq
    all_queue_key = mq.get_all_queue_keys()  # set of queue_key
    qkey_map = {
            # 'p2p_gossip': [],
            'metrics_timer':[],
            'metrics_flow':[],
            'metrics_counter':[],
            'vnode_status':[],
            'xsync_interval':[],
            'kadinfo':[],
            "p2pbroadcast":[],
            "txpool_state":[],
            "txpool_receipt":[],
            "txpool_cache":[],
            "metrics_alarm":[],
            "metrics_array_counter":[],
            "p2ptest_sendrecord":[],
            "p2ptest_send_info":[],
            "p2ptest_recv_info":[],
            "relayer_gas":[],
            }

    for qkey in all_queue_key:
        # if qkey.find('p2p_gossip') != -1:
        #     qkey_map['p2p_gossip'].append(qkey)
        if qkey.find('metrics_timer')!=-1:
            qkey_map['metrics_timer'].append(qkey)
        if qkey.find('metrics_flow')!=-1:
            qkey_map['metrics_flow'].append(qkey)
        if qkey.find('metrics_counter')!=-1:
            qkey_map['metrics_counter'].append(qkey)
        if qkey.find('vnode_status')!=-1:
            qkey_map['vnode_status'].append(qkey)
        if qkey.find('xsync_interval')!=-1:
            qkey_map['xsync_interval'].append(qkey)
        if qkey.find('kadinfo')!=-1:
            qkey_map['kadinfo'].append(qkey)
        if qkey.find('p2pbroadcast')!=-1:
            qkey_map['p2pbroadcast'].append(qkey)
        if qkey.find('txpool_state')!=-1:
            qkey_map['txpool_state'].append(qkey)
        if qkey.find('txpool_receipt')!=-1:
            qkey_map['txpool_receipt'].append(qkey)
        if qkey.find('txpool_cache')!=-1:
            qkey_map['txpool_cache'].append(qkey)
        if qkey.find('metrics_alarm')!=-1:
            qkey_map['metrics_alarm'].append(qkey)
        if qkey.find('metrics_array_counter')!=-1:
            qkey_map['metrics_array_counter'].append(qkey)
        if qkey.find('p2ptest_sendrecord')!=-1:
            qkey_map['p2ptest_sendrecord'].append(qkey)
        if qkey.find('p2ptest_send_info')!=-1:
            qkey_map['p2ptest_send_info'].append(qkey)
        if qkey.find('p2ptest_recv_info')!=-1:
            qkey_map['p2ptest_recv_info'].append(qkey)
        if qkey.find('relayer_gas')!=-1:
            qkey_map['relayer_gas'].append(qkey)
        

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

        for qkey in qkey_map.get('vnode_status'):
            consumer = vnode_status_consumer.VnodeStatusConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('xsync_interval'):
            consumer = xsync_interval_consumer.XsyncIntervalConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('kadinfo'):
            consumer = p2p_kadinfo_consumer.P2pKadinfoConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('p2pbroadcast'):
            consumer = p2p_broadcast_consumer.P2pBroadcastConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('txpool_state'):
            consumer = txpool_state_consumer.TxpoolStateConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)

        for qkey in qkey_map.get('txpool_receipt'):
            consumer = txpool_receipt_consumer.TxpoolReceiptConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
            
        for qkey in qkey_map.get('txpool_cache'):
            consumer = txpool_cache_consumer.TxpoolCacheConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('metrics_alarm'):
            consumer = metrics_alarm_consumer.MetricsAlarmConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)

        for qkey in qkey_map.get('metrics_array_counter'):
            consumer = metrics_array_counter_consumer.MetricsArrayCounterConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('p2ptest_sendrecord'):
            consumer = p2ptest_sendrecord_consumer.P2PTestSendRecordConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('p2ptest_send_info'):
            consumer = p2ptest_send_consumer.P2PTestSendConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('p2ptest_recv_info'):
            consumer = p2ptest_recv_consumer.P2PTestRecvConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
            consumer_list.append(consumer)
        
        for qkey in qkey_map.get('relayer_gas'):
            consumer = relayer_gas_consumer.RelayerGasConsumer(q=mq,queue_key_list=[qkey],alarm_env=alarm_env)
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
