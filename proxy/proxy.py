#!/usr/bin/env python
#-*- coding:utf8 -*-

from flask import Flask ,request,jsonify
import sys
import json

import os
import copy
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
log_path = os.path.join(project_path, "log/topargus-proxy.log")
os.environ['LOG_PATH'] =  log_path
from common.slogging import slog
import common.slogging as slogging
import common.my_queue as my_queue
import common.config as sconfig

app = Flask(__name__)
mq = my_queue.RedisQueue(host= sconfig.REDIS_HOST, port=sconfig.REDIS_PORT, password=sconfig.REDIS_PASS)

gconfig_shm_file = sconfig.SHM_GCONFIG_FILE
gconfig = sconfig.PROXY_CONFIG

def dump_gconfig():
    global gconfig, gconfig_shm_file
    with open(gconfig_shm_file,'w') as fout:
        fout.write(json.dumps(gconfig))
        slog.info('dump gconfig:{0} to file:{1}'.format(json.dumps(gconfig), gconfig_shm_file))
        fout.close()
    return

def load_gconfig():
    global gconfig_shm_file
    new_config = None
    with open(gconfig_shm_file,'r') as fin:
        new_config = json.loads(fin.read())
        fin.close()
    slog.info(new_config)
    return new_config

dump_gconfig()


@app.route('/')
def hello_world():
    return 'TOP-DW test ok!\n'

#config update
@app.route('/api/config/',methods=['GET'])
@app.route('/api/config',methods=['GET'])
def config_update():
    alarm_ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote_addr
    slog.info("/api/config clientip:{0} method:{1}".format(alarm_ip, request.method))
    global gconfig
    status_ret = {
            0:'OK',
            -1:'权限验证失败',
            -2:'格式转化出错，请检查字段数或者字段格式等',
            -3: '不支持的方法',
            }
    ret = {}
    if request.method == 'GET':
        new_config = load_gconfig()
        slog.info(new_config)
        if new_config:
            gconfig = copy.deepcopy(new_config)
            slog.debug('load gconfig from shm:{0}'.format(json.dumps(gconfig)))
        ret = {'status': 0, 'error': status_ret.get(0), 'config': gconfig, 'ip': alarm_ip}
        return jsonify(ret)
    return

# get public ip
@app.route('/api/ip/',methods=['GET'])
@app.route('/api/ip',methods=['GET'])
def get_public_ip():
    alarm_ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote_addr
    slog.info("/api/ip clientip:{0} method:{1}".format(alarm_ip, request.method))
    ret = {'status': 0, 'ip': alarm_ip}
    return jsonify(ret)


#告警上报(发包收包情况收集)
@app.route('/api/alarm/', methods=['POST'])
@app.route('/api/alarm', methods=['POST'])
def alarm_report():
    payload =  {}
    if not request.is_json:
        payload = json.loads(request.data)
    else:
        payload = request.get_json()
    # print(payload)
    ret = {'status':''}
    status_ret = {
            0:'OK',
            -1:'上报字段不合法,部分可能上传失败',
            -2:'格式转化出错，请检查字段数或者字段格式等'
            }
    if not payload.get('data'):
        ret = {'status': -2, 'error': status_ret.get(-2)}
        return jsonify(ret)

    alarm_ip = request.headers.get('X-Forwarded-For') or request.headers.get('X-Real-IP') or request.remote_addr
    # slog.info("recv alarm from ip:{0} size:{1}".format(alarm_ip, len(payload.get('data'))))
    # mq.handle_alarm(payload.get('data'))
    mq.handle_alarm_env_ip(payload.get('data'), payload.get('env'), payload.get('public_ip'))
    ret = {'status': 0, 'error': status_ret.get(0)}
    return jsonify(ret)


def run():
    slog.info('proxy start...')
    slogging.start_log_monitor()
    # app.run(host="127.0.0.1", port= 9092, debug=True)
    app.run()
    return


if __name__ == '__main__':
    run()
