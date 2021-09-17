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

consumer_process_count = 13
proxy_gunicorn_process_count = 5
dash_process_count = 2
disk_need_clen = False

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

def now_time_utc_hour() -> int:
    tz = datetime.timezone(datetime.timedelta(hours=0))
    date_now = datetime.datetime.now(tz)
    t_hour = date_now.hour
    return t_hour

def yesterday_date_str() -> str:
    tz = datetime.timezone(datetime.timedelta(hours=0))
    date_now = datetime.datetime.now(tz)
    last_date_day = date_now.date()-datetime.timedelta(days=1)
    str_date = str(last_date_day).replace('-', '')
    # str like '20210818'
    return str_date

def send_alarm_to_dingding(type: str, content):
    webhook = config.WEBHOOK
    header = {"Content-Type": "application/json"}

    template = alarm_template[type]
    print(template)
    address_name = config.ADDRESS_USAGE
    template["markdown"]["text"] = "{0} \n > [{1}](http://{2}/center) \n".format(content, address_name, my_ip)

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
        self.disk_usage_rate = 0

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
        res = subprocess.call('cd {0} && date | xargs echo > proxy/log/topargus-proxy.log'.format(project_path),shell=True)
        print(res)
        if self.inner_restart_dashboard_interval == restart_dashboard_interval:
            # print(self.inner_restart_dashboard_interval)
            self.inner_restart_dashboard_interval = 0
            
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

    def check_disk_free(self,disk_name):
        global disk_need_clen
        res = int(subprocess.getoutput('df -mh | grep %s |awk -F \' \' \'{print $5}\' ' % disk_name ).strip('%'))
        if res > 88:
            disk_need_clen = True
        if res > 90 and res != self.disk_usage_rate:
            content = "\n[info] disk space less than 10%! Already use " + \
                str(res) + " %"
            send_alarm_to_dingding("info",content)
        
        self.disk_usage_rate = res
        
        return

class database_checker:
    def __init__(self):
        f = open('database_info.json', 'r')
        str = f.read()
        f.close()
        print(str)
        self.metrics_alarm_database_dict = json.loads(str)
        self.consensus_succ_rate_hold = 80
        self.alarm_check_interval = 5
    
    def get_ip_size(self,db_name:str):
        query_sql = 'SELECT count(public_ips) as res from ips_table;'
        res = myquery.query_database(db_name,query_sql)[0]['res']
        return res

    def sum_consensus_result_into_map(self,res_item,res_map,perfix_str:str):
        for item in res_item:
            public_ip = item['public_ip']
            value = item['value']
            if public_ip not in res_map:
                res_map[public_ip] = {
                }
            if perfix_str+'begin' not in res_map[public_ip]:
                res_map[public_ip][perfix_str+'sum'] = 0
                res_map[public_ip][perfix_str+'begin'] = value
                res_map[public_ip][perfix_str+'end'] = value
            if value < res_map[public_ip][perfix_str+'end']:
                # print("in:",public_ip,res_map[public_ip][perfix_str+'begin'],res_map[public_ip][perfix_str+'end'],res_map[public_ip][perfix_str+'sum'])
                res_map[public_ip][perfix_str+'sum'] += (res_map[public_ip][perfix_str+'end']-res_map[public_ip][perfix_str+'begin'])
                # print("in:",public_ip,res_map[public_ip][perfix_str+'begin'],res_map[public_ip][perfix_str+'end'],res_map[public_ip][perfix_str+'sum'])
                res_map[public_ip][perfix_str+'begin'] = value
                res_map[public_ip][perfix_str+'end'] = value
            else:
                res_map[public_ip][perfix_str+'end'] = value
        
        for _ip,_res in res_map.items():
            # print(_ip,_res[perfix_str+'begin'],_res[perfix_str+'end'],_res[perfix_str+'sum'])
            _res[perfix_str+'sum'] += (_res[perfix_str+'end'] - _res[perfix_str+'begin'])
            # print(_ip,_res[perfix_str+'begin'],_res[perfix_str+'end'],_res[perfix_str+'sum'])
        return

    def do_check_consensus_succ_rate2(self,db_name:str) ->list:
        res_map = {}
        query_succ_sql = 'SELECT public_ip,value from metrics_counter where category = "cons" and tag = "tableblock_leader_finish_succ" order by public_ip,send_timestamp;'
        succ_res_item = myquery.query_database(db_name,query_succ_sql)
        self.sum_consensus_result_into_map(succ_res_item,res_map,"succ")

        query_fail_sql = 'SELECT public_ip,value from metrics_counter where category = "cons" and tag = "tableblock_leader_finish_fail" order by public_ip,send_timestamp;'
        fail_res_item = myquery.query_database(db_name,query_fail_sql)
        self.sum_consensus_result_into_map(fail_res_item,res_map,"fail")

        # ip_list = []
        missing_ip = []
        unqualified_list = []
        query_ip_sql = 'SELECT public_ips from ips_table;'
        ip_item = myquery.query_database(db_name,query_ip_sql)
        for _each in ip_item:
            _ip = _each['public_ips']
            if _ip not in res_map.keys():
                missing_ip.append(_ip)
                continue
            if 'succsum' not in res_map[_ip].keys() or 'failsum' not in res_map[_ip].keys():
                missing_ip.append(_ip)
                continue
            succ_num = res_map[_ip]['succsum']
            fail_num = res_map[_ip]['failsum']
            if fail_num !=0 :
                cal_rate = round(succ_num / (succ_num + fail_num) * 100,2)
                # print(_ip,cal_rate)
                if cal_rate< self.consensus_succ_rate_hold:
                    unqualified_list.append((_ip,cal_rate,succ_num,succ_num+fail_num))
        
        report_data = '## 【共识成功率检测结果】\n 日期：{0} \n 来自数据库： {1} \n '.format(yesterday_date_str(),db_name)
        
        if len(missing_ip):
            missing_report = '### 缺少节点数据：\n '
            for _ip in missing_ip:
                missing_report = missing_report + "\n - " + _ip
            report_data = report_data + missing_report+ '\n\n'

        qualified_report = '### 成功率高于{0}%节点个数： \n **【{1}/{2}】** \n'.format(self.consensus_succ_rate_hold, len(ip_item)-len(missing_ip)-len(unqualified_list), len(ip_item))
        report_data = report_data + qualified_report

        if len(unqualified_list):
            unqualified_list.sort(key=lambda k: k[1]) # sort by rate
            unqualified_report = '### 成功率低于{0}%：【{1}】 个 \n [format: ip: rate (succ/all) ] '.format(self.consensus_succ_rate_hold, len(unqualified_list))
            for _d in unqualified_list:
                unqualified_report = unqualified_report + ' \n - {0}: {1}% ({2} / {3})'.format(_d[0],_d[1],_d[2],_d[3])
            report_data = report_data + unqualified_report

        report_list = [report_data]
        # print(report_list)
        return report_list

    #[unused]
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
            if cal_rate < 80:
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
        if list_cnt and first_flag:
            res_list.append(res_perfix + unqualified_list)
        elif list_cnt:
            res_list.append(unqualified_list)

        return res_list

    def do_sumarize_report(self,db_name:str):
        content_list = []
        for _r in self.do_check_consensus_succ_rate2(db_name):
            content_list.append(_r)
        return content_list

    def check_yesterday_db(self,database_list:list):
        yesterday_date = yesterday_date_str()
        # check at every day 1:00UTC (+8:00 = 9:00am) the yesterday database
        for _database in database_list:
            _database_name = _database['name']
            if(_database_name.endswith(yesterday_date) and not self.metrics_alarm_database_dict[_database_name]["done_report"] ):
                content_list = self.do_sumarize_report(_database_name)
                for each_content in content_list:
                    send_alarm_to_dingding('info', each_content)
                    # if is_mainnet_db(_database_name):
                    #     send_alarm_to_dingding_common('info', each_content)
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
                
                content = "\n  INFO  \n\n  检查到数据库被清理  \n {0} was deleted".format(
                    _e_database)
                send_alarm_to_dingding('info', content)
                update_sql = 'DELETE FROM db_setting where db_name = "{0}" ;'.format(_e_database)
                myquery.query_database('empty', update_sql)
        print(del_list)
        for _del_database in del_list:
            del(self.metrics_alarm_database_dict[_del_database])


    def database_setting_update(self,database_list:list):
        query_sql = "SELECT * from db_setting;"
        query_item = myquery.query_database('empty',query_sql)
        print(query_item)
        db_list = [_item['db_name'] for _item in query_item]
        print(db_list)
        for _database in database_list:
            _database_name = _database['name']
            _database_time = _database['time']
            _database_size = _database['db_size']
            _database_ip_cnt = _database['ip_cnt']

            if _database_name not in db_list:
                insert_sql = 'INSERT INTO `db_setting`(`db_name`,`create_time`,`db_size`,`ip_cnt`) VALUES("{0}","{1}","{2}","{3}");'.format(_database_name,_database_time,_database_size,_database_ip_cnt)
                myquery.query_database('empty',insert_sql)
            else:
                update_sql = 'UPDATE `db_setting` SET `db_size`="{0}",`ip_cnt`={1} WHERE db_name = "{2}";'.format(_database_size,_database_ip_cnt,_database_name)
                myquery.query_database('empty',update_sql)



    def do_clean(self,database_name:str):
        content = "\n  INFO  \n\n  数据库被清理  \n {0} was deleted automaticly by spider".format(database_name)
        send_alarm_to_dingding('info', content)

        update_sql = 'DELETE FROM db_setting where db_name = "{0}" ;'.format(database_name)
        delete_sql = 'DROP DATABASE `{0}` ;'.format(database_name)
        
        del(self.metrics_alarm_database_dict[database_name])
        myquery.query_database('empty', update_sql)
        myquery.query_database('empty', delete_sql)
        return

    def database_clean(self,database_list:list):
        global disk_need_clen
        if not disk_need_clen:
            return
        query_sql = "SELECT * from db_setting;"
        query_item = myquery.query_database('empty',query_sql)
        res_item = {}
        for _item in query_item:
            res_item[_item['db_name']] = _item['reserve']
        # print(res_item)
        for _database in database_list:
            _database_name = _database['name']
            if res_item[_database_name] == 'false':
                # print(_database_name)
                # do clean
                self.do_clean(_database_name)
                disk_need_clen = False
                return

    def get_detailed_metrics_alarm_info(self, db_name, old_size, size) -> list:
        query_sql = 'SELECT send_timestamp,public_ip,category,tag from `metrics_alarm` where seq_id > {0} and seq_id <= {1}'.format(old_size, size)
        query_items = myquery.query_database(db_name, query_sql)
        if not query_items:
            return []

        category_tag_cnt = {}
        public_ip_cnt = {}
        max_ts = 0
        min_ts = int(time.time())
        for _each in query_items:
            public_ip = _each['public_ip']
            category = _each['category']
            tag = _each['tag']
            st = _each['send_timestamp']
            if st > max_ts: max_ts = st
            if st < min_ts: min_ts = st
            if public_ip not in public_ip_cnt:
                public_ip_cnt[public_ip] = 1
            else:
                public_ip_cnt[public_ip] += 1
            if category+tag not in category_tag_cnt:
                category_tag_cnt[category+tag] = 1
            else:
                category_tag_cnt[category+tag] += 1

        report_data = '## 【METRICS_ALARM】 新增{0}条 \n > 来自数据库： {1} \n seq_id: {2} - {3} \n'.format(size-old_size, db_name, old_size,size)

        time_report = '\n ### 时间范围: \n \n > {0} - {1}'.format(time.strftime(format_regex, time.localtime(min_ts)),time.strftime(format_regex, time.localtime(max_ts)))

        report_data = report_data + time_report + ' \n \n '

        category_report = '\n ### 分类占比: \n'
        for ct, num in category_tag_cnt.items():
            category_report = category_report + \
                ' \n -  {0} 个 {1} '.format(str(num), str(ct))
        report_data = report_data + category_report + ' \n \n '

        ip_report = '\n ### 来源ip占比: \n'
        for ip, num in public_ip_cnt.items():
            ip_report = ip_report + ' \n - {0} 个来自 {1} '.format(str(num), str(ip))
        report_data = report_data + ip_report + ' \n \n '

        return [report_data]

    def check_metrics_alarm(self, database_list: list):
        if self.alarm_check_interval < 5:
            self.alarm_check_interval += 1
            return
        else:
            self.alarm_check_interval = 0

        for _database in database_list:
            _database_name = _database['name']
            query_sql = 'SELECT table_rows from information_schema.tables where table_schema = "{0}" and table_name = "metrics_alarm";'.format(_database_name)


            query_items = myquery.query_database(_database_name, query_sql)
            size = query_items[0]['table_rows']

            old_size = self.metrics_alarm_database_dict[_database_name]["alarm_size"]

            if size > old_size:
                content_list = self.get_detailed_metrics_alarm_info(_database_name,old_size,size)
                for each_content in content_list:
                    send_alarm_to_dingding('info',each_content)
                    # if is_mainnet_db(_database_name):
                    #     send_alarm_to_dingding_common('info',each_content)
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

def database_detailed_info() -> list:
    db_size_query_sql = 'SELECT TABLE_SCHEMA, round( sum( DATA_LENGTH / 1024 / 1024 ), 2 ) AS data_size, round( sum( INDEX_LENGTH / 1024 / 1024 ),2 ) AS index_size FROM information_schema.TABLES GROUP BY table_schema ORDER BY data_size DESC;'
    db_size_items = myquery.query_database('empty', db_size_query_sql)
    # print(db_size_items)
    db_size_dict = {}
    for item in db_size_items:
        # print(item)
        if item['TABLE_SCHEMA'] not in database_ignore_list:
            db_size_dict[item['TABLE_SCHEMA']] = str(item['data_size'])+'MB + ' + str(item['index_size']) + 'MB = ' + str(round((item['data_size']+item['index_size'])/1024, 2)) + 'GB'
    # print('-------')
    # print(db_size_dict)

    ip_size_query_sql = 'SELECT TABLE_SCHEMA, TABLE_ROWS from information_schema.TABLES WHERE TABLE_NAME = "ips_table";'
    ip_size_item = myquery.query_database('empty', ip_size_query_sql)
    # print(ip_size_item)
    ip_size_dict = {}
    for item in ip_size_item:
        # print(item)
        if item['TABLE_SCHEMA'] not in database_ignore_list:
            ip_size_dict[item['TABLE_SCHEMA']] = item['TABLE_ROWS']
    # print('-------')
    # print(ip_size_dict)


    query_sql = 'SELECT TABLE_SCHEMA,CREATE_TIME FROM information_schema.TABLES WHERE TABLE_NAME = "metrics_counter";'
    query_items = myquery.query_database('empty', query_sql)
    res_list = []
    for item in query_items:
        if item['TABLE_SCHEMA'] not in database_ignore_list:
            res_list.append({
                'time': '['+str(item['CREATE_TIME'])+']',
                'name': item['TABLE_SCHEMA'],
                'db_size': db_size_dict[item['TABLE_SCHEMA']],
                'ip_cnt': ip_size_dict[item['TABLE_SCHEMA']],
            })
    res_list.sort(key=lambda k: k['time'])
    return res_list
    
    

    

def run():
    db_c = database_checker()
    process_c = process_checker()
    send_alarm_to_dingding('info','spider_start')
    while True:
        
        process_c.check_true_or_restart('consumer/','main_consumer.py',consumer_process_count,'nohup python3 main_consumer.py -t test & \n')
        process_c.check_true_or_restart('proxy/','gunicorn',proxy_gunicorn_process_count,'nohup gunicorn -w 4 -b 127.0.0.1:9092 proxy:app & \n')
        process_c.check_true_or_restart('dashboard/','dash.py',dash_process_count,'nohup python3 dash.py & \n')
        process_c.restart_dash('dashboard/','dash.py','nohup python3 dash.py & \n')
        process_c.check_disk_free('vda1')

        database_list = database_time()
        db_c.check_database(database_list)
        # db_c.check_metrics_alarm(database_list)
        if now_time_utc_hour() == 1:
            db_c.check_yesterday_db(database_list)
        db_c.database_setting_update(database_detailed_info())
        db_c.database_clean(database_list)
        db_c.dump_to_file()
        time.sleep(check_interval)


if __name__ == '__main__':
    run()
