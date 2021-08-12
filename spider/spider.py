import time
import datetime
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
    template["markdown"]["text"] = "#### http://{0}/center \n{1}".format(
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
    
    def get_ip_size(self,db_name:str):
        query_sql = 'SELECT count(public_ips) as res from ips_table;'
        res = myquery.query_database(db_name,query_sql)[0]['res']
        return res

    def do_check_consensus_succ_rate(self,db_name:str) -> list:
        gmt_time = int(time.time()/300)*300
        begin_gmt_time = gmt_time-25*3600
        end_gmt_time = gmt_time-3600
        ip_list_size = self.get_ip_size(db_name)
        print(ip_list_size)
        begin_item = []
        end_item = []
        for _ in range(0, 47):
            begin_gmt_time += 1800
            begin_sql = 'SELECT public_ip,tag,count,value from metrics_counter where category = "cons" and tag in ("tableblock_leader_finish_succ","tableblock_leader_finish_fail") and send_timestamp<{0} group by public_ip,tag;'.format(
                begin_gmt_time)
            begin_item = myquery.query_database(db_name, begin_sql)
            if(len(begin_item) == 2*ip_list_size):
                break
        for _ in range(0, 47):
            end_gmt_time -= 1800
            end_sql = 'SELECT public_ip,tag,count,value from metrics_counter where category = "cons" and tag in ("tableblock_leader_finish_succ","tableblock_leader_finish_fail") and send_timestamp>{0} group by public_ip,tag;'.format(
                end_gmt_time)
            end_item = myquery.query_database(db_name, end_sql)
            if(len(end_item) == 2*ip_list_size):
                break

        res_item = {}
        for item in begin_item:
            public_ip = item['public_ip']
            tag = item['tag']
            count = item['count']
            value = item['value']
            if public_ip not in res_item:
                res_item[public_ip] = {
                    'begin_succ':0,
                    'end_succ':0,
                    'begin_fail':0,
                    'end_fail':0
                }
            if tag == 'tableblock_leader_finish_succ':
                res_item[public_ip]['begin_succ'] = value
            if tag == 'tableblock_leader_finish_fail':
                res_item[public_ip]['begin_fail'] = value
        for item in end_item:
            public_ip = item['public_ip']
            tag = item['tag']
            count = item['count']
            value = item['value']
            if public_ip not in res_item:
                res_item[public_ip] = {
                    'begin_succ':0,
                    'end_succ':0,
                    'begin_fail':0,
                    'end_fail':0
                }
            if tag == 'tableblock_leader_finish_succ':
                res_item[public_ip]['end_succ'] = value
            if tag == 'tableblock_leader_finish_fail':
                res_item[public_ip]['end_fail'] = value
        
        cal_res = {}
        for _public_ip,_data in res_item.items():
            cal_res[_public_ip] = {
                'succ_delta':0,
                'fail_delta':0,
            }
            if _data['end_succ'] < _data['begin_succ'] or _data['end_fail'] < _data['begin_fail']:
                cal_res[_public_ip]['succ_delta'] = _data['end_succ']
                cal_res[_public_ip]['fail_delta'] = _data['end_fail']
            else:
                cal_res[_public_ip]['succ_delta'] = _data['end_succ'] - _data['begin_succ']
                cal_res[_public_ip]['fail_delta'] = _data['end_fail'] - _data['begin_fail']
        
        res_list = []
        res_perfix = '#### 共识成功率检测结果\n 时间范围：[{0} - {1}] \n env: {2} \n'.format(time.strftime(format_regex, time.localtime(begin_gmt_time)),time.strftime(format_regex, time.localtime(end_gmt_time)),db_name)
        unqualified_list_perfix = " unqualified_list: [ip rate succ/all]"
        unqualified_list = unqualified_list_perfix
        list_cnt = 0
        first_flag = True
        for _public_ip,_cal_res in cal_res.items():
            if _cal_res['succ_delta'] == 0 and _cal_res['fail_delta'] == 0: 
                print("continue")
                continue
            cal_rate = round(_cal_res['succ_delta'] / (_cal_res['succ_delta']+_cal_res['fail_delta']) * 100,2)
            if cal_rate < 98:
                unqualified_list = unqualified_list + "\n - {0} : {1}% ({2}/{3})".format(
                    _public_ip, cal_rate, _cal_res['succ_delta'], _cal_res['succ_delta']+_cal_res['fail_delta'])
                list_cnt +=1
            else:
                print('{0} pass : {1}% ({2}/{3})'.format(_public_ip,cal_rate, _cal_res['succ_delta'], _cal_res['succ_delta']+_cal_res['fail_delta']))
            if list_cnt >= 15:
                if first_flag:
                    res_list.append(res_perfix + unqualified_list)
                    first_flag = False
                else:
                    res_list.append(unqualified_list)
                unqualified_list = unqualified_list_perfix
                list_cnt = 0
        if first_flag:
            res_list.append(res_perfix + unqualified_list)
        else:
            res_list.append(unqualified_list)

        return res_list

    def do_sumarize_report(self,db_name:str):
        content_list = []
        for _r in self.do_check_consensus_succ_rate(db_name):
            content_list.append(_r)
        return content_list

    def check_yesterday_db(self,database_list:list):
        tz = datetime.timezone(datetime.timedelta(hours=0))
        date_now = datetime.datetime.now(tz)
        last_date_day = date_now.date()-datetime.timedelta(days=1)
        str_date = str(last_date_day).replace('-', '')
        t_hour = date_now.hour
        if(t_hour == 1):
            # check at every day 1:00UTC (+8:00 = 9:00am)
            for _database in database_list:
                _database_name = _database['name']
                if(_database_name.endswith(str_date) and not self.metrics_alarm_database_dict[_database_name]["done_report"]):
                    content_list = self.do_sumarize_report(_database_name)
                    for each_content in content_list:
                        send_alarm_to_dingding('info', each_content)
                        time.sleep(1)
                    self.metrics_alarm_database_dict[_database_name]["done_report"] = 1

        return


    def check_database(self, database_list: list):
        for _database in database_list:
            _database_name = _database['name']
            _database_time = _database['time']
 
            if _database_name not in self.metrics_alarm_database_dict:
                # each database info template
                self.metrics_alarm_database_dict[_database_name] = {
                    "alarm_size": 0,
                    "done_report": 0,
                }
                content = "\n  INFO  \n\n  新数据库创建  \n {0} was created at time {1}".format(
                    _database_name, _database_time)
                send_alarm_to_dingding('info', content)
        n_database_l = [_d['name'] for _d in database_list]
        del_list = []
        for _e_database in self.metrics_alarm_database_dict:
            if _e_database not in n_database_l:
                del_list.append(_e_database)
                
                content = "\n  INFO  \n\n  数据库被清理  \n {0} was deleted".format(
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
                content = "\n  ALARM  \n\n  新增 {0} 条 metrics_alarm \n database:[{1}]".format(
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
        db_c.check_yesterday_db(database_list)
        db_c.dump_to_file()
        time.sleep(check_interval)


if __name__ == '__main__':
    run()
