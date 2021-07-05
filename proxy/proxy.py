#!/usr/bin/env python
#-*- coding:utf8 -*-

from flask import Flask ,request,jsonify
import sys
import json

import os
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

@app.route('/')
def hello_world():
    return 'TOP-DW test ok!\n'


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
    slog.info("recv alarm from ip:{0} size:{1}".format(alarm_ip, len(payload.get('data'))))
    mq.handle_alarm(payload.get('data'))
    ret = {'status': 0, 'error': status_ret.get(0)}
    return jsonify(ret)


def run():
    slog.info('proxy start...')
    slogging.start_log_monitor()
    app.run(host="127.0.0.1", port= 9092, debug=True)
    #app.run()
    return


if __name__ == '__main__':
    run()
