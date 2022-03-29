import time

import socket
import requests
import sys
import json
import subprocess

import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
log_path = os.path.join(project_path, "log/topargus-consumer.log")
os.environ['LOG_PATH'] = log_path

import common.config as config



def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '0.0.0.0'
    finally:
        s.close()
    return IP


my_ip = get_local_ip()


check_interval = 60

spider_process_count = 2


project_path = '/home/charles/project/top-dw-server'
format_regex = '%Y-%m-%d %H:%M:%S'

alarm_template = {
    "down": {"msgtype": "markdown",
             "markdown": {
                 "title": "[dw_down]",
                 "text": "",
             },
             "at": {
                 "atUserIds": [],
                 "isAtAll": False
             }},
    "alarm": {"msgtype": "markdown",
              "markdown": {
                  "title": "[dw_alarm]",
                  "text": "",
              },
              "at": {
                  "atUserIds": [],
                  "isAtAll": False
              }},
    "info": {"msgtype": "markdown",
             "markdown": {
                 "title": "[dw_info]",
                 "text": "",
             },
             "at": {
                 "atUserIds": [],
                 "isAtAll": False
             }},
}

def now_time():
    return time.strftime(format_regex, time.localtime(time.time()))


def send_alarm_to_dingding(type: str, content):
    webhook_PRI = config.WEBHOOK_PRI
    # webhook_PUB = config.WEBHOOK_PUB
    header = {"Content-Type": "application/json"}

    template = alarm_template[type]
    print(template)
    address_name = config.ADDRESS_USAGE
    template["markdown"]["text"] = "{0} \n > [{1}](http://{2}/center) \n".format(content, address_name, my_ip)

    send_data = json.dumps(template)
    print(send_data)

    try:
        r = requests.post(webhook_PRI, headers=header,
                          data=send_data, timeout=10)
        print(r.text)
    except Exception as e:
        print('catch exception:{0}'.format(e))
    
    # if type == 'info':    
    #     try:
    #         r = requests.post(webhook_PUB, headers=header,
    #                         data=send_data, timeout=10)
    #         print(r.text)
    #     except Exception as e:
    #         print('catch exception:{0}'.format(e))
        


class process_checker:
    def __init__(self):
        pass

    def check_true_or_restart(self,component_path:str,process_name:str,expected_num:int,start_cmd:str):
        res = subprocess.getoutput('ps -ef |grep {0} | grep -v grep | grep -v nohup -c'.format(process_name))
        
        print("{0} cnt {1}, expected {2}".format(process_name,res,expected_num))
        if int(res) !=expected_num:
            content = "\n[down] {0} num: {1}/{2} try to restart at {3}".format(
                process_name, res, expected_num, now_time())
            send_alarm_to_dingding("down",content)
            print("try restart {0}, time: {1}".format(process_name,now_time()))
            cmd_str = "ps -ef |grep " + process_name + " | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9"
            print(cmd_str)
            res = subprocess.getoutput(cmd_str)
            print(res)
            res = subprocess.call("cd {0} && source vvlinux/bin/activate && cd {1} && {2}".format(project_path,component_path,start_cmd),shell=True)
            time.sleep(1)
            print(res)

def run():
    process_c = process_checker()
    send_alarm_to_dingding('alarm','spider_alive start')
    while True:
        process_c.check_true_or_restart('spider/','spider.py',spider_process_count,'python3 -u spider.py & \n')
        time.sleep(check_interval)

if __name__ == '__main__':
    run()
