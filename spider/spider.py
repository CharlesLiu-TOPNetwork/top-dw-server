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
from dashboard import query_core

myquery = query_core.Dash()


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
restart_dashboard_interval = 180 # every three hours

consumer_process_count = 22
proxy_process_count = 2
dash_process_count = 2

project_path = '/home/charles/project/top-dw-server'
format_regex = '%Y-%m-%d %H:%M:%S'

alarm_template = {
    "down": {"msgtype": "markdown",
             "markdown": {
                 "title": "[dw_down]",
                 "text": "",
             },
             "at": {
                 "atUserIds": ['CharlesLiu'],
                 "isAtAll": False
             }},
    "alarm": {"msgtype": "markdown",
              "markdown": {
                         "title": "[dw_alarm]",
                         "text": "",
              },
              "at": {
                  "atUserIds": [],
                  "isAtAll": True
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
    webhook = config.WEBHOOK
    header = {"Content-Type": "application/json"}

    template = alarm_template[type]
    print(template)
    template["markdown"]["text"] = "#### http://{0}/center {1}".format(
        my_ip, content)

    send_data = json.dumps(template)
    print(send_data)

    try:
        r = requests.post(webhook, headers=header,
                          data=send_data, timeout=10)
        print(r.text)
    except Exception as e:
        print('catch exception:{0}'.format(e))


class process_checker:
    def __init__(self):
        self.inner_restart_dashboard_interval = 0 # counter

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

    def restart_dash(self,component_path:str,process_name:str,start_cmd:str):

        if self.inner_restart_dashboard_interval == restart_dashboard_interval:
            # print(self.inner_restart_dashboard_interval)
            self.inner_restart_dashboard_interval = 0
            
            res = subprocess.call('cd {0} && date | xargs echo > keep_alive_tools/nohup.out'.format(project_path),shell=True)
            print(res)
            print("try kill && restart dashboard  && clear log.")
            
            cmd_str = "ps -ef |grep " + process_name + " | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9"
            print(cmd_str)
            res = subprocess.getoutput(cmd_str)
            print(res)
            res = subprocess.call("cd {0} && source vvlinux/bin/activate && cd {1} && {2}".format(project_path,component_path,start_cmd),shell=True)
            time.sleep(1)
        else:
            self.inner_restart_dashboard_interval +=1

        return

class database_checker:
    def __init__(self):
        f = open('database_info.json', 'r')
        str = f.read()
        f.close()
        print(str)
        self.metrics_alarm_database_dict = json.loads(str)


    def check_database(self, database_list: list):
        for _database in database_list:
            _database_name = _database['name']
            _database_time = _database['time']

            if _database_name not in self.metrics_alarm_database_dict:
                # each database info template
                self.metrics_alarm_database_dict[_database_name] = {
                    "alarm_size": 0,
                }
                content = "\n[info]new database {0} was created at time {1}".format(
                    _database_name, _database_time)
                send_alarm_to_dingding('info', content)
        n_database_l = [_d['name'] for _d in database_list]
        del_list = []
        for _e_database in self.metrics_alarm_database_dict:
            if _e_database not in n_database_l:
                del_list.append(_e_database)
                
                content = "\n[info]database {0} was deleted ".format(
                    _e_database)
                send_alarm_to_dingding('info', content)
        print(del_list)
        for _del_database in del_list:
            del(self.metrics_alarm_database_dict[_del_database])


    def check_metrics_alarm(self, database_list: list):
        for _database in database_list:
            _database_name = _database['name']
            query_sql = 'SELECT table_rows from information_schema.tables where table_schema = "{0}" and table_name = "metrics_alarm";'.format(_database_name)


            query_items = myquery.query_database(_database_name, query_sql)
            size = query_items[0]['table_rows']

            old_size = self.metrics_alarm_database_dict[_database_name]["alarm_size"]

            if size > old_size:
                content = "\n{0} metrics_alarm generated in database:[{1}]".format(
                    size-old_size, _database_name)
                send_alarm_to_dingding('alarm', content)
            else:
                print("no more alarm in {0}".format(_database_name))

            self.metrics_alarm_database_dict[_database_name]["alarm_size"] = size

    def dump_to_file(self):
        log = json.dumps(self.metrics_alarm_database_dict)
        print(log)
        f = open('database_info.json', 'w+')
        f.write(log)
        f.close()


database_ignore_list = ['information_schema', 'mysql',
                        'performance_schema', 'empty', 'None', 'test_database_name']
# ![inner_function] query_databases_with_create_time


def database_time() -> list:
    query_sql = 'SELECT TABLE_SCHEMA,CREATE_TIME FROM information_schema.TABLES WHERE TABLE_NAME = "metrics_counter";'
    query_items = myquery.query_database('empty', query_sql)
    res_list = []
    for item in query_items:
        if item['TABLE_SCHEMA'] not in database_ignore_list:
            res_list.append({
                'time': '['+str(item['CREATE_TIME'])+']',
                'name': item['TABLE_SCHEMA'],
            })
    res_list.sort(key=lambda k: k['time'])
    return res_list


def run():
    db_c = database_checker()
    process_c = process_checker()
    while True:
        
        process_c.check_true_or_restart('consumer/','main_consumer.py',consumer_process_count,'nohup python3 main_consumer.py -t test & \n')
        process_c.check_true_or_restart('proxy/','proxy.py',proxy_process_count,'nohup python3 proxy.py & \n')
        process_c.check_true_or_restart('dashboard/','dash.py',dash_process_count,'nohup python3 dash.py & \n')
        process_c.restart_dash('dashboard/','dash.py','nohup python3 dash.py & \n')

        database_list = database_time()
        db_c.check_database(database_list)
        db_c.check_metrics_alarm(database_list)
        db_c.dump_to_file()
        time.sleep(check_interval)


if __name__ == '__main__':
    run()