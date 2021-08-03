import time
import socket
import requests
import sys
import json
import argparse

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
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '0.0.0.0'
    finally:
        s.close()
    return IP


my_ip = get_local_ip()


check_interval = 60


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


class checker:
    def __init__(self):
        f = open('database_info.json', 'r')
        str = f.read()
        f.close()
        print(str)
        self.metrics_alarm_database_dict = json.loads(str)

    def send_alarm_to_dingding(self,type: str, content):
        webhook = config.WEBHOOK
        header = {"Content-Type": "application/json"}

        template = alarm_template[type]
        print(template)
        template["markdown"]["text"] = "#### http://{0}/center {1}".format(
            my_ip, content)

        send_data = json.dumps(template)

        try:
            r = requests.post(webhook, headers=header,
                              data=send_data, timeout=10)
            print(r.text)
        except Exception as e:
            print('catch exception:{0}'.format(e))

    def check_database(self, database_list: list):
        for _database in database_list:
            _database_name = _database['name']
            _database_time = _database['time']

            if _database_name not in self.metrics_alarm_database_dict:
                # each database info template
                self.metrics_alarm_database_dict[_database_name] = {
                    "alarm_size": 0,
                }
                content = "\n[info]new database {0} was create at time {1}".format(
                    _database_name, _database_time)
                self.send_alarm_to_dingding('info', content)
        n_database_l = [_d['name'] for _d in database_list]
        del_list = []
        for _e_database in self.metrics_alarm_database_dict:
            if _e_database not in n_database_l:
                del_list.append(_e_database)
                
                content = "\n[info]database {0} was deleted ".format(
                    _e_database)
                self.send_alarm_to_dingding('info', content)
        print(del_list)
        for _del_database in del_list:
            del(self.metrics_alarm_database_dict[_del_database])


    def check_metrics_alarm(self, database_list: list):
        for _database in database_list:
            _database_name = _database['name']
            query_sql = 'SELECT count(seq_id) as max_seq_id FROM metrics_alarm;'
            # print(query_sql,_database)

            query_items = myquery.query_database(_database_name, query_sql)
            size = query_items[0]['max_seq_id']

            old_size = self.metrics_alarm_database_dict[_database_name]["alarm_size"]

            if size > old_size:
                content = "\n{0} metrics_alarm was generate in database:[{1}]".format(
                    size-old_size, _database_name)
                self.send_alarm_to_dingding('alarm', content)
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
    s = checker()
    while True:
        database_list = database_time()
        s.check_database(database_list)
        s.check_metrics_alarm(database_list)
        s.dump_to_file()
        # send_alarm_to_dingding("down","test_content")
        time.sleep(check_interval)


if __name__ == '__main__':
    run()
