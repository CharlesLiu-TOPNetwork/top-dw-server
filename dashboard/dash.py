#!/usr/bin/env python
#-*- coding:utf8 -*-


import os,sys
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))

log_path = os.path.join(project_path, "log/topargus-dash.log")
os.environ['LOG_PATH'] =  log_path
import common.slogging as slogging
from common.slogging import slog



from flask import Flask ,request, url_for, render_template,jsonify
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import json
# import requests
# import redis
# import uuid
import time
# import random
# import base64
# import copy
# import threading
# import dash_core
from dashboard import dash_user
from dashboard import query_core
# from common.my_queue import TopArgusRedis
# import common.config as sconfig

app = Flask(__name__)
auth = HTTPBasicAuth()

user_info = {
    'root': generate_password_hash('root')
    }

myuser = dash_user.User()
myquery = query_core.Dash()

@auth.verify_password
def verify_password(username, password):
    global user_info
    print('username:{0}'.format(username))
    if username not in user_info:
        tmp_user_info = myuser.get_user_info()
        if tmp_user_info:
            slog.info('update user_info from db:{0}'.format(json.dumps(tmp_user_info)))
            for item in tmp_user_info:
                if item.get('username') not in user_info:
                    user_info[item.get('username')] = item.get('password_hash')
        else:
            slog.info('update user_info from db failed')

    if username not in user_info:
        return False
    if not check_password_hash(user_info.get(username), password):
        tmp_user_info = myuser.get_user_info()
        if not tmp_user_info:
            return False
        slog.info('update user_info from db:{0}'.format(json.dumps(tmp_user_info)))
        for item in tmp_user_info:
            if item.get('username') != username:
                continue
            user_info[username] = item.get('password_hash')

    return check_password_hash(user_info.get(username), password)

@app.route('/')
# @auth.login_required
def hello_world():
    return '{0} Hello, World!'.format(auth.username())


# !?[unfinished][raw_data_api]
@app.route('/dw-api/metrics',methods=['GET'])
@app.route('/dw-api/metrics/',methods=['GET'])
# @auth.login_required
def query_metrics():
    env = request.args.get('env') or None
    ip = request.args.get('ip') or None
    type = request.args.get('type') or None
    category = request.args.get('category') or None
    tag = request.args.get('tag') or None

    sql = ''
    # http://161.35.114.185/dw-api/metrics/?env=local_test&ip=192.168.181.128&type=counter&category=vhost&tag=recv_msg
    # http://161.35.114.185/dw-api/metrics/?env=local_test&ip=192.168.181.128&type=timer&category=vhost&tag=handle_data_filter
    # http://161.35.114.185/dw-api/metrics/?env=local_test&ip=192.168.181.128&type=flow&category=vhost&tag=handle_data_ready_called

    if type == "counter":
        #SELECT send_timestamp,count,value FROM metrics_counter WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "recv_msg";
        sql = 'SELECT send_timestamp,count,value FROM metrics_counter WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}";'.format(
            ip, category, tag)
    elif type == "timer":
        #SELECT send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "handle_data_filter";
        sql = 'SELECT send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}";'.format(
            ip, category, tag)
    elif type == "flow":
        #SELECT send_timestamp,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "handle_data_ready_called";
        sql = 'SELECT send_timestamp,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}";'.format(
            ip, category, tag)
    else:
        return 'wrong type for now'
    
    slog.info(sql)

    return jsonify(myquery.query_database(env,sql))

'''
@app.route('/test',methods=['GET'])
@app.route('/test/',methods=['GET'])
def test_echart():
    query_items = myquery.query_database('local_diff', 'SELECT public_ip,send_timestamp,count,max_time FROM metrics_timer WHERE category = "blockstore" AND tag = "sync_store_block_time" ORDER BY public_ip,send_timestamp;')
    # query_items = myquery.query_database('local_diff', 'SELECT public_ip,send_timestamp,count,value FROM metrics_counter WHERE category = "vhost" AND tag = "recv_msg" ORDER BY public_ip,send_timestamp;')
    # print(query_items)
    res_item = {}
    x_list = []
    data_list = {}
    for item in query_items:
        ip = item['public_ip']
        if ip not in res_item:
            res_item[ip] = {}
        if ip not in data_list:
            data_list[ip] = []

        ts = item['send_timestamp']
        if ts not in x_list:
            x_list.append(ts)
        
        if ts not in res_item[ip]:
            res_item[ip][ts] = {}
        res_item[ip][ts]['count'] = item['count']
        # res_item[ip][ts]['value'] = item['value']
        res_item[ip][ts]['max_time'] = item['max_time']
    
    for _ip,_list in data_list.items():
        # print(_ip,_list)
        for ts in x_list:
            # print(_ip,ts)
            if ts in res_item[_ip]:
                _list.append(res_item[_ip][ts]['max_time'])
            else:
                _list.append(0)
            # _list.append(res_item[_ip][ts]['count'] or None)
    # print(data_list)

    # print(res_item)
    # print(x_list)

    return render_template('multi.html.j2',  x_list = x_list, data_list = data_list)

# ?[test][unstable] tmp test 
@app.route('/tmp',methods=['GET'])
@app.route('/tmp/',methods=['GET'])
def tmp():
    query_sql = 'SHOW DATABASES;'
    query_items = myquery.query_database('empty',query_sql)
    # return jsonify(query_items)
    res_list = []
    for item in query_items:
        if item['Database'] not in database_ignore_list:
            res_list.append(item['Database'])
    # print(res_list)
        
    return render_template('query_center/aggregated_by_ip_2.html.j2', database_list=res_list)

# ?[test][unstable][unfinished] test sync
@app.route('/xsync_tmp',methods=['GET'])
@app.route('/xsync_tmp/',methods=['GET'])
def xsync_tmp():

    return render_template('test_sync_tmp.html')

# ?[test][unfinished] query_one_metrics tag. get all ips.
@app.route('/query_metrics',methods=['GET'])
@app.route('/query_metrics/',methods=['GET'])
def test_echart2():
    # http://161.35.114.185/query_metrics?database=local_diff&table=metrics_timer&wanted=max_time&category=blockstore&tag=store_block_time
    # http://161.35.114.185/query_metrics?database=local_diff&table=metrics_flow&wanted=tps&category=vhost&tag=handle_data_ready_called
    database = request.args.get('database') or None
    table = request.args.get('table') or None
    wanted = request.args.get('wanted') or None
    category = request.args.get('category') or None
    tag = request.args.get('tag') or None
    return query_one(database, table, wanted, category, tag)

def query_one(database,table,wanted,category,tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,'+ wanted +' FROM ' + table + ' WHERE category = "' + category + '" AND tag = "' + tag + '" ORDER BY public_ip,send_timestamp;'
    # print(query_sql)
    query_items = myquery.query_database(database,query_sql)
    # print(query_items)

    res_item = {}
    x_list = []
    data_list = {}
    for item in query_items:
        ip = item['public_ip']
        if ip not in res_item:
            res_item[ip] = {}
        if ip not in data_list:
            data_list[ip] = []

        ts = item['send_timestamp']
        if ts not in x_list:
            x_list.append(ts)
        
        if ts not in res_item[ip]:
            res_item[ip][ts] = {}
        res_item[ip][ts]['count'] = item['count']
        res_item[ip][ts][wanted] = item[wanted]
    
    x_list.sort()

    for _ip,_list in data_list.items():
        # print(_ip,_list)
        for ts in x_list:
            # print(_ip,ts)
            if ts in res_item[_ip]:
                _list.append(res_item[_ip][ts][wanted])
            else:
                _list.append(0)
    # print(data_list)

    # print(res_item)
    # print(x_list)

    return render_template('multi.html.j2', x_list = format_timestamp_list(x_list), data_list = data_list)

'''

# ![function] used by other apis, return an [category - tag - type:counter]'s all nodes' metrics data (one full picture)
def query_counter(database, category, tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,value FROM metrics_counter WHERE category = "' + \
        category + '" AND tag = "' + tag + '" ORDER BY public_ip,send_timestamp;'
    query_items = myquery.query_database(database, query_sql)

    res_item = {}
    x_list = []
    data_lists = {
        'count': {},
        'value': {},
    }
    for item in query_items:
        ip = item['public_ip']
        if ip not in res_item:
            res_item[ip] = {}
        for _key, _val in data_lists.items():
            if ip not in data_lists[_key]:
                data_lists[_key][ip] = []
        ts = item['send_timestamp']
        if ts not in x_list:
            x_list.append(ts)
        if ts not in res_item[ip]:
            res_item[ip][ts] = {}
        res_item[ip][ts]['count'] = item['count']
        res_item[ip][ts]['value'] = item['value']

    x_list.sort()

    for _key, data_list in data_lists.items():
        for _ip, _list in data_list.items():
            for ts in x_list:
                if ts in res_item[_ip]:
                    _list.append(res_item[_ip][ts][_key])
                else:
                    _list.append(0)

    # print(data_lists)
    res = render_template('joint/body_div_line.html', name=category+tag)
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name=_key)
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag)
    return res

# ![function] used by other apis, return an [category - tag - type:flow]'s all nodes' metrics data (one full picture)
def query_flow(database, category, tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE category = "' + \
        category + '" AND tag = "' + tag + '" ORDER BY public_ip,send_timestamp;'
    query_items = myquery.query_database(database, query_sql)

    res_item = {}
    x_list = []
    data_lists = {
        'count': {},
        'max_flow': {},
        'min_flow': {},
        'sum_flow': {},
        'avg_flow': {},
        'tps_flow': {},
        'tps': {},
    }
    for item in query_items:
        ip = item['public_ip']
        if ip not in res_item:
            res_item[ip] = {}
        for _key, _val in data_lists.items():
            if ip not in data_lists[_key]:
                data_lists[_key][ip] = []
        ts = item['send_timestamp']
        if ts not in x_list:
            x_list.append(ts)
        if ts not in res_item[ip]:
            res_item[ip][ts] = {}
        res_item[ip][ts]['count'] = item['count']
        res_item[ip][ts]['max_flow'] = item['max_flow']
        res_item[ip][ts]['min_flow'] = item['min_flow']
        res_item[ip][ts]['sum_flow'] = item['sum_flow']
        res_item[ip][ts]['avg_flow'] = item['avg_flow']
        res_item[ip][ts]['tps_flow'] = item['tps_flow']
        res_item[ip][ts]['tps'] = item['tps']

    x_list.sort()

    for _key, data_list in data_lists.items():
        for _ip, _list in data_list.items():
            for ts in x_list:
                if ts in res_item[_ip]:
                    _list.append(res_item[_ip][ts][_key])
                else:
                    _list.append(None)

    # print(data_lists)
    res = render_template('joint/body_div_line.html', name=category+tag)
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name=_key)
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag)
    return res

# ![function] used by other apis, return an [category - tag - type:timer]'s all nodes' metrics data (one full picture)
def query_timer(database, category, tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE category = "' + \
        category + '" AND tag = "' + tag + '" ORDER BY public_ip,send_timestamp;'
    query_items = myquery.query_database(database, query_sql)

    res_item = {}
    x_list = []
    data_lists = {
        'count': {},
        'max_time': {},
        'min_time': {},
        'avg_time': {},
    }
    for item in query_items:
        ip = item['public_ip']
        if ip not in res_item:
            res_item[ip] = {}
        for _key, _val in data_lists.items():
            if ip not in data_lists[_key]:
                data_lists[_key][ip] = []
        ts = item['send_timestamp']
        if ts not in x_list:
            x_list.append(ts)
        if ts not in res_item[ip]:
            res_item[ip][ts] = {}
        res_item[ip][ts]['count'] = item['count']
        res_item[ip][ts]['max_time'] = item['max_time']
        res_item[ip][ts]['min_time'] = item['min_time']
        res_item[ip][ts]['avg_time'] = item['avg_time']

    x_list.sort()

    for _key, data_list in data_lists.items():
        for _ip, _list in data_list.items():
            for ts in x_list:
                if ts in res_item[_ip]:
                    _list.append(res_item[_ip][ts][_key])
                else:
                    _list.append(0)

    # print(data_lists)
    res = render_template('joint/body_div_line.html', name=category+tag)
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name=_key)
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag)
    return res

# ![api] return an [category - tag - type]'s all nodes' metrics data (one full picture)
@app.route('/query_category_tag_metrics',methods=['GET'])
@app.route('/query_category_tag_metrics/',methods=['GET'])
def query_category_tag_metrics():
    database = request.args.get('database') or None
    type = request.args.get('type') or None
    category = request.args.get('category') or None
    tag = request.args.get('tag') or None

    if type == 'counter':
        return query_counter(database, category, tag)
    elif type == 'flow':
        return query_flow(database, category, tag)
    elif type == 'timer':
        return query_timer(database, category, tag)
    else:
        return "query_category_tag_metrics"  


# ![api] return an [ip - category]'s all metrics data (a long long div)
@app.route('/query_ip_category_metrics',methods=['GET'])
@app.route('/query_ip_category_metrics/',methods=['GET'])
def query_ip_category_metrics():
    database = request.args.get('database') or None
    ip = request.args.get('public_ip') or None
    category = request.args.get('category') or None

    # metrics_counter:
    query_sql = 'SELECT tag,send_timestamp,count,value FROM metrics_counter WHERE public_ip = "{0}" AND category = "{1}" ORDER BY tag,send_timestamp;'.format(ip, category)
    query_items = myquery.query_database(database,query_sql)
    res_item = {}
    for item in query_items:
        tag = item['tag']
        if tag not in res_item:
            res_item[tag] = {
                'list_x' : [],
                'value_series' : {
                    'count':[],
                    'value':[],
                },
            }
        ts = item['send_timestamp']
        res_item[tag]['list_x'].append(ts)
        res_item[tag]['value_series']['count'].append(item['count'])
        res_item[tag]['value_series']['value'].append(item['value'])

    res = render_template('joint/body_div_line.html', name = "metrics_counter")
    for _tag,_value in res_item.items():
        res = res + render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip.html.j2', name=_tag,
                                    value_series=_value['value_series'], list_x=format_timestamp_list(_value['list_x']), append_info = '[' + database + ']' + category + '_' + ip)


    res = res + render_template('joint/body_div_line.html', name = "metrics_timer")
    # metrics_timer:
    query_sql = 'SELECT tag,send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE public_ip = "{0}" AND category = "{1}" ORDER BY tag,send_timestamp;'.format(ip, category)
    query_items = myquery.query_database(database,query_sql)
    res_item = {}
    for item in query_items:
        tag = item['tag']
        if tag not in res_item:
            res_item[tag] = {
                'list_x' : [],
                'value_series' : {
                    'count':[],
                    'max_time':[],
                    'min_time':[],
                    'avg_time':[],
                },
            }
        ts = item['send_timestamp']
        res_item[tag]['list_x'].append(ts)
        res_item[tag]['value_series']['count'].append(item['count'])
        res_item[tag]['value_series']['max_time'].append(item['max_time'])
        res_item[tag]['value_series']['min_time'].append(item['min_time'])
        res_item[tag]['value_series']['avg_time'].append(item['avg_time'])

    for _tag,_value in res_item.items():
        res = res + render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip.html.j2', name=_tag,
                                    value_series=_value['value_series'], list_x=format_timestamp_list(_value['list_x']), append_info = '[' + database + ']' + category + '_' + ip)
    
    res = res + render_template('joint/body_div_line.html', name = "metrics_flow")
    # metrics_flow:
    query_sql = 'SELECT tag,send_timestamp,count,max_flow,min_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE public_ip = "{0}" AND category = "{1}" ORDER BY tag,send_timestamp;'.format(ip, category)
    query_items = myquery.query_database(database,query_sql)
    res_item = {}
    for item in query_items:
        tag = item['tag']
        if tag not in res_item:
            res_item[tag] = {
                'list_x' : [],
                'value_series' : {
                    'count':[],
                    'max_flow':[],
                    'min_flow':[],
                    'avg_flow':[],
                    'tps_flow':[],
                    'tps':[],
                },
            }
        ts = item['send_timestamp']
        res_item[tag]['list_x'].append(ts)
        res_item[tag]['value_series']['count'].append(item['count'])
        res_item[tag]['value_series']['max_flow'].append(item['max_flow'])
        res_item[tag]['value_series']['min_flow'].append(item['min_flow'])
        res_item[tag]['value_series']['avg_flow'].append(item['avg_flow'])
        res_item[tag]['value_series']['tps_flow'].append(item['tps_flow'])
        res_item[tag]['value_series']['tps'].append(item['tps'])

    for _tag,_value in res_item.items():
        res = res + render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip.html.j2', name=_tag,
                                    value_series=_value['value_series'], list_x = format_timestamp_list(_value['list_x']), append_info = '[' + database + ']' + category + '_' + ip)


    return res


# ![api] return an [ip - category - tag] one metrics data (a div)
@app.route('/query_ip_category_tag_metrics_counter',methods=['GET'])
@app.route('/query_ip_category_tag_metrics_counter/',methods=['GET'])
def query_ip_category_tag_metrics_counter():
    database = request.args.get('database') or None
    ip = request.args.get('public_ip') or None
    category = request.args.get('category') or None
    tag = request.args.get('tag') or None

    # metrics_counter:
    query_sql = 'SELECT tag,send_timestamp,count,value FROM metrics_counter WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}" ORDER BY send_timestamp;'.format(ip, category,tag)
    query_items = myquery.query_database(database,query_sql)
    res_item = {
        'list_x': [],
        'value_series': {
            'count': [],
            'value': [],
        },
    }
    for item in query_items:
        ts = item['send_timestamp']
        res_item['list_x'].append(ts)
        res_item['value_series']['count'].append(item['count'])
        res_item['value_series']['value'].append(item['value'])

    # res = render_template('joint/body_div_line.html', name = "metrics_counter")
    # res = ""
    # for _tag,_value in res_item.items():
    return render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip.html.j2', name=tag,
                                    value_series=res_item['value_series'], list_x = format_timestamp_list(res_item['list_x']), append_info = '[' + database + ']' + category + '_' + ip)


    # res = res + render_template('joint/body_div_line.html', name = "metrics_timer")

    return res


# ![help_tools] convert a [list] into a [str] which skip the None data
def format_data_list_to_str(data_list: dict):
    res = {}
    for _ip, _list in data_list.items():
        res_list_str = ",".join([str(x) if x else ' ' for x in _list])
        res_list_str = '[' + res_list_str + ']'
        res[_ip] = res_list_str
    return res

# ![help_tools] convert unix_timestamp list to human-readable type
format_regex = '%Y-%m-%d %H:%M:%S'
def format_timestamp_list(l:list):
    res_list = []
    for v in l:
        res_list.append(time.strftime(format_regex, time.localtime(v)))
    return res_list

# ![help_tools] convert a [list] into a [str] which skip the None data
def format_sync_data_list_to_str(ip_list:list,input_map:dict):
    res_map = {}
    for ts,item in input_map.items():
        format_ts = time.strftime(format_regex, time.localtime(ts))
        res_map[format_ts] = {
            'self_min_str': "",
            'self_gap_str': "",
            'peer_min_str': "",
            'peer_gap_str': "",
        }
        for _ip in ip_list:
            if _ip not in item:
                res_map[format_ts]['self_min_str'] += ","
                res_map[format_ts]['self_gap_str'] += ","
                res_map[format_ts]['peer_min_str'] += ","
                res_map[format_ts]['peer_gap_str'] += ","
            else:
                res_map[format_ts]['self_min_str'] += str(
                    input_map[ts][_ip][0])+","
                res_map[format_ts]['self_gap_str'] += str(
                    input_map[ts][_ip][1]-input_map[ts][_ip][0])+","
                res_map[format_ts]['peer_min_str'] += str(
                    input_map[ts][_ip][2])+","
                res_map[format_ts]['peer_gap_str'] += str(
                    input_map[ts][_ip][3]-input_map[ts][_ip][2])+","
    # print(res_map)
    return res_map


#![help_tools] convert a [list] into a [str] which skip the None data
def format_cache_hit_data_list_to_str(tag_list: list, input_map: dict):
    res_map = {}
    for ts, item in input_map.items():
        format_ts = time.strftime(format_regex, time.localtime(ts))
        res_map[format_ts] = {
            'hit': "",
            'miss': "",
            'sum': "",
        }
        for _tag in tag_list:
            if _tag not in item:
                res_map[format_ts]['hit'] += ","
                res_map[format_ts]['miss'] += ","
                res_map[format_ts]['sum'] += ","
            else:
                res_map[format_ts]['hit'] += str(input_map[ts][_tag][1])+","
                res_map[format_ts]['miss'] += str(input_map[ts][_tag][0]-input_map[ts][_tag][1])+","
                # {name:'cat2',value:260},
                if input_map[ts][_tag][0]!=0:
                    res_map[format_ts]['sum'] += "{name:'"+_tag + "',value:" + str(input_map[ts][_tag][0]) +"},"
                else:
                    res_map[format_ts]['sum'] += "{name:'"+_tag + "',value:null},"

    return res_map

#![help_tools] convert a [list] into a [str]
def format_compared_cache_hit_data_list_to_str(tag_list:list,input_map:dict):
    res_map = {}
    for ts, item in input_map.items():
        format_ts = time.strftime(format_regex, time.localtime(ts))
        res_map[format_ts] = {
            'n1_hit': "",
            'n1_miss': "",
            'n2_hit': "",
            'n2_miss': "",
        }
        for _tag in tag_list:
            if _tag not in item:
                res_map[format_ts]['n1_hit'] += ","
                res_map[format_ts]['n1_miss'] += ","
                res_map[format_ts]['n2_hit'] += ","
                res_map[format_ts]['n2_miss'] += ","
            else:
                res_map[format_ts]['n1_hit'] += str(
                    input_map[ts][_tag]['p1_v'])+","
                res_map[format_ts]['n1_miss'] += str(
                    input_map[ts][_tag]['p1_c']-input_map[ts][_tag]['p1_v'])+","
                res_map[format_ts]['n2_hit'] += str(
                    input_map[ts][_tag]['p2_v'])+","
                res_map[format_ts]['n2_miss'] += str(
                    input_map[ts][_tag]['p2_c']-input_map[ts][_tag]['p2_v'])+","
                
    return res_map


database_ignore_list = ['information_schema', 'mysql', 'performance_schema', 'empty', 'None','test_database_name']

# ![inner_function] query_databases_with_create_time
def database_time() -> list:
    query_sql = 'SELECT TABLE_SCHEMA,CREATE_TIME FROM information_schema.TABLES WHERE TABLE_NAME = "metrics_counter";'
    query_items = myquery.query_database('empty',query_sql)
    res_list = []
    for item in query_items:
        if item['TABLE_SCHEMA'] not in database_ignore_list:
            res_list.append({
                'time':'['+str(item['CREATE_TIME'])+']',
                'name':item['TABLE_SCHEMA'],
            })
    res_list.sort(key=lambda k: k['time'])
    return res_list

# ![page] query one ip , return all metrics data
@app.route('/ip_metrics',methods=['GET'])
@app.route('/ip_metrics/',methods=['GET'])
def ip_metrics():
    return render_template('query_center/aggregated_by_ip.html.j2', database_list = database_time())

# ![page] query one tag , return all ips' metrics data
@app.route('/one_metrics',methods=['GET'])
@app.route('/one_metrics/',methods=['GET'])
def one_metrics():
    return render_template('query_center/aggregated_by_tag.html.j2', database_list = database_time())

# ![page] query one table address sync interval
@app.route('/xsync',methods=['GET'])
@app.route('/xsync/',methods=['GET'])
def xsync():
    return render_template('query_center/special_packet_xsync_interval.html.j2',database_list = database_time())


# ![page] query_blockstore cache rate
@app.route('/xblockstore',methods=['GET'])
@app.route('/xblockstore/',methods=['GET'])
def xblockstore():
    return render_template('query_center/special_packet_xblockstore_cache.html.j2',database_list = database_time())

# ![page][center]
@app.route('/center',methods=['GET'])
@app.route('/center/',methods=['GET'])
def center_page():
    return render_template('query_center/center.html')

# ![api] query blockstore && statestore cache hit 
@app.route('/query_state_block_store_cache_hit_rate',methods=['GET'])
@app.route('/query_state_block_store_cache_hit_rate/',methods=['GET'])
def query_store_cache_hit():
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    store_type = request.args.get('store_type') or None

    res_page = ""
    query_sql = 'SELECT send_timestamp, tag, count, value FROM `metrics_counter` WHERE category = "{0}" AND tag REGEXP "access_from*" AND public_ip = "{1}";'.format(
        store_type, public_ip)
    query_items = myquery.query_database(database,query_sql)
    if not query_items:
        res_page += "None data with "+store_type
    else:
        res_map = {}
        tag_list = []
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            tag = item['tag'][12:] # access_from
            if ts not in res_map:
                res_map[ts]={}
            if ts not in ts_list:
                ts_list.append(ts)
            if tag not in res_map[ts]:
                res_map[ts][tag] = []
            if tag not in tag_list:
                tag_list.append(tag)
            res_map[ts][tag].append(item['count'])
            res_map[ts][tag].append(item['value'])
        ts_list.sort()
        res_page += render_template('joint/body_big_line_chart_for_cache_rate.html.j2',name = public_ip + " "+ store_type,ts_list = format_timestamp_list(ts_list),tag_list = tag_list,res_map = format_cache_hit_data_list_to_str(tag_list,res_map))

    return res_page

# ![api] query blockstore && statestore cache hit compare two ip
@app.route('/query_state_block_store_compared_cache_hit_rate',methods=['GET'])
@app.route('/query_state_block_store_compared_cache_hit_rate/',methods=['GET'])
def query_store_compared_cache_hit():
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    store_type = request.args.get('store_type') or None
    o_public_ip = request.args.get('o_public_ip') or None
    res_page = ""
    query_sql = 'SELECT send_timestamp, tag, count, value FROM `metrics_counter` WHERE category = "{0}" AND tag REGEXP "access_from*" AND public_ip = "{1}";'.format(
        store_type, public_ip)
    query_items = myquery.query_database(database,query_sql)

    if not query_items:
        res_page += "None data with " + public_ip + " " + store_type
    else:
        res_map = {}
        tag_list = []
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            tag = item['tag'][12:] # access_from
            if ts not in res_map:
                res_map[ts]={}
            if ts not in ts_list:
                ts_list.append(ts)
            if tag not in res_map[ts]:
                res_map[ts][tag] = {
                    "p1_c":0,
                    "p1_v":0,
                    "p2_c":0,
                    "p2_v":0,
                }
            if tag not in tag_list:
                tag_list.append(tag)
            res_map[ts][tag]["p1_c"]=item['count']
            res_map[ts][tag]["p1_v"]=item['value']
        # o_public_ip
        query_sql = 'SELECT send_timestamp, tag, count, value FROM `metrics_counter` WHERE category = "{0}" AND tag REGEXP "access_from*" AND public_ip = "{1}";'.format(
        store_type, o_public_ip)
        query_items = myquery.query_database(database,query_sql)

        if not query_items:
            res_page += "None data with " + o_public_ip + " " + store_type
        else:
            for item in query_items:
                ts = item['send_timestamp']
                tag = item['tag'][12:] # access_from
                if ts not in res_map:
                    res_map[ts]={}
                if ts not in ts_list:
                    ts_list.append(ts)
                if tag not in res_map[ts]:
                    res_map[ts][tag] = {
                        "p1_c":0,
                        "p1_v":0,
                        "p2_c":0,
                        "p2_v":0,
                    }
                if tag not in tag_list:
                    tag_list.append(tag)
                res_map[ts][tag]["p2_c"]=item['count']
                res_map[ts][tag]["p2_v"]=item['value']
            ts_list.sort()
            res_page += render_template('joint/body_big_line_chart_for_compare_cache_rate.html.j2', 
                                        name = public_ip + " & " + o_public_ip + " " + store_type, 
                                        ts_list = format_timestamp_list(ts_list), 
                                        tag_list = tag_list, 
                                        res_map = format_compared_cache_hit_data_list_to_str(tag_list, res_map), 
                                        public_ip = public_ip, 
                                        o_public_ip = o_public_ip)

    return res_page


# ![api] query xblockstore [hit-miss]
@app.route('/query_xblockstore_hit',methods=['GET'])
@app.route('/query_xblockstore_hit/',methods=['GET'])
def query_xblockstore_hit():
    # database = request.args.get('database') or None
    # public_ip = request.args.get('public_ip') or None
    # category = "blockstore"
    # query_tags_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + category + '" and type = "counter" ;'
    # query_items = myquery.query_database(database,query_tags_sql)
    # tag_list = [l['tag'] for l in query_items]
    # print(tag_list)

    # res_page = ""
    # query_sql = 'SELECT send_timestamp, tag, count, value FROM `metrics_counter` WHERE category = "blockstore" AND tag REGEXP "access_from*" AND public_ip = "{0}";'.format(public_ip)
    # query_items = myquery.query_database(database,query_sql)
    # if not query_items:
    #     res_page += "None data with blockstore"
    # else:
    #     res_map = {}
    #     tag_list = []
    #     ts_list = []
    #     for item in query_items:
    #         ts = item['send_timestamp']
    #         tag = item['tag']
    #         if ts not in res_map:
    #             res_map[ts]={}
    #         if ts not in ts_list:
    #             ts_list.append(ts)
    #         if tag not in res_map[ts]:
    #             res_map[ts][tag] = []
    #         if tag not in tag_list:
    #             tag_list.append(tag)
    #         res_map[ts][tag].append(item['count'])
    #         res_map[ts][tag].append(item['value'])
    #     ts_list.sort()
    #     res_page += render_template('joint/body_big_line_chart_for_cache_rate.html.j2',name = public_ip + " blockstore",ts_list = format_timestamp_list(ts_list),tag_list = tag_list,res_map = format_cache_hit_data_list_to_str(tag_list,res_map))


    # print(res_map)

    return render_template('tmp_blockstore.html')
    return res_page


# ![api] query xsync_interval
@app.route('/query_xsync_interval',methods=['GET'])
@app.route('/query_xsync_interval/',methods=['GET'])
def query_xsync_interval():
    database = request.args.get('database') or None
    table_address = request.args.get('table_address') or None
    
    res_page = render_template('joint/body_div_line.html',name = "mode: fast")

    query_sql = 'SELECT send_timestamp,public_ip,self_min,self_max,peer_min,peer_max from xsync_interval where table_address = "{0}" and sync_mod = "fast";'.format(table_address)
    query_items = myquery.query_database(database,query_sql)
    if not query_items:
        res_page += "None data with fast sync" 
    else:
        res_map = {}
        ip_list = []
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            ip = item['public_ip']
            if ts not in res_map:
                res_map[ts] = {}
            if ts not in ts_list:
                ts_list.append(ts)
            if ip not in res_map[ts]:
                res_map[ts][ip] = [] 
            if ip not in ip_list:
                ip_list.append(ip)       
            res_map[ts][ip].append(item['self_min'])
            res_map[ts][ip].append(item['self_max'])
            res_map[ts][ip].append(item['peer_min'])
            res_map[ts][ip].append(item['peer_max'])
        res_page += render_template('joint/body_big_line_chart_for_xsync.html.j2',name = table_address + "/fast",ts_list = format_timestamp_list(ts_list),ip_list = ip_list,res_map = format_sync_data_list_to_str(ip_list, res_map))

    res_page += render_template('joint/body_div_line.html',name = "mode: full")

    query_sql = 'SELECT send_timestamp,public_ip,self_min,self_max,peer_min,peer_max from xsync_interval where table_address = "{0}" and sync_mod = "full";'.format(table_address)
    query_items = myquery.query_database(database,query_sql)
    if not query_items:
        res_page+="None data with full sync"
    else:
        res_map = {}
        ip_list = []
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            ip = item['public_ip']
            if ts not in res_map:
                res_map[ts] = {}
            if ts not in ts_list:
                ts_list.append(ts)
            if ip not in res_map[ts]:
                res_map[ts][ip] = [] 
            if ip not in ip_list:
                ip_list.append(ip)       
            res_map[ts][ip].append(item['self_min'])
            res_map[ts][ip].append(item['self_max'])
            res_map[ts][ip].append(item['peer_min'])
            res_map[ts][ip].append(item['peer_max'])
        res_page += render_template('joint/body_big_line_chart_for_xsync.html.j2',name = table_address + "/full",ts_list = format_timestamp_list(ts_list),ip_list = ip_list,res_map = format_sync_data_list_to_str(ip_list, res_map))
        
    return res_page

# ![api] query one [database - ip] vnode status
@app.route('/query_ip_vnode_status',methods=['GET'])
@app.route('/query_ip_vnode_status/',methods=['GET'])
def query_ip_vnode_status():    
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    query_sql = 'SELECT timestamp,rec,zec,auditor,validator,archive,edge from vnode_status where public_ip = "'+ public_ip+'" ORDER BY timestamp;'
    query_items = myquery.query_database(database,query_sql)
    list_x = []
    res_item = {
        'rec' : [],
        'zec': [],
        'auditor': [],
        'validator': [],
        'archive': [],
        'edge': [],
    }
    for item in query_items:
        ts = item['timestamp']
        list_x.append(ts)
        res_item['rec'].append(item['rec'])
        res_item['zec'].append(item['zec'])
        res_item['auditor'].append(item['auditor'])
        res_item['validator'].append(item['validator'])
        res_item['archive'].append(item['archive'])
        res_item['edge'].append(item['edge'])

    res = render_template('joint/body_center_line_chart_for_vnode_status.html.j2',
                          name='vnode_status', value_series=res_item, list_x=format_timestamp_list(list_x),append_info = public_ip)
    return res

# ![api] query one database ips
@app.route('/query_ips',methods=['GET'])
@app.route('/query_ips/',methods=['GET'])
def query_ips():
    database = request.args.get('database') or None
    query_sql = 'SELECT public_ips FROM ips_table;'
    query_items = myquery.query_database(database,query_sql)
    res_list = []
    for item in query_items:
        res_list.append(item['public_ips'])
    # print(res_list)
    return render_template('query_center/query_ips.html.j2',ip_lists = res_list)

# ![api] query one database category
@app.route('/query_categorys',methods=['GET'])
@app.route('/query_categorys/',methods=['GET'])
def query_categorys():
    database = request.args.get('database') or None
    query_sql = 'SELECT DISTINCT category FROM tags_table;'
    query_items = myquery.query_database(database,query_sql)
    res_list = []
    for item in query_items:
        res_list.append(item['category'])
    # print(res_list)
    return render_template('query_center/query_categorys.html.j2',category_lists = res_list)

# ![api] query one database tag
@app.route('/query_tags',methods=['GET'])
@app.route('/query_tags/',methods=['GET'])
def query_tags():
    database = request.args.get('database') or None
    category = request.args.get('category') or None
    type = request.args.get('type') or None
    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + category + '" and type = "' + type + '" ;'
    query_items = myquery.query_database(database,query_sql)
    # print(query_sql,query_items)
    res_list = []
    for item in query_items:
        res_list.append(item['tag'])
    # print(res_list)
    return render_template('query_center/query_tags.html.j2',tag_lists = res_list)


# !?[unfinished][function] deceide if tags should be multi-page by size
def if_pages(tags:list):
    res = ""
    if len(tags)<=12:
        for _tag in tags:
            res = res + render_template('joint/body_small_empty_for_one_metrics_tag_one_ip.html.j2',name = _tag)
    else:
        res = render_template("joint/body_pages_for_tags.html.j2")
    return res

# !?[unfinished][api] query one database tag raw
@app.route('/query_tags_raw',methods=['GET'])
@app.route('/query_tags_raw/',methods=['GET'])
def query_tags_raw():
    database = request.args.get('database') or None
    category = request.args.get('category') or None

    res_list = {
        "metrics_counter": [],
        "metrics_timer": [],
        "metrics_flow": [],
    }

    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + \
        category + '" and type = "counter" ;'
    query_items = myquery.query_database(database, query_sql)
    for item in query_items:
        res_list["metrics_counter"].append(item['tag'])

    res = render_template('joint/body_div_line.html', name="metrics_counter")
    res = res+if_pages(res_list["metrics_counter"])

    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + \
        category + '" and type = "timer" ;'
    query_items = myquery.query_database(database, query_sql)
    for item in query_items:
        res_list["metrics_timer"].append(item['tag'])

    res = res + render_template('joint/body_div_line.html', name="metrics_timer")
    res = res+if_pages(res_list["metrics_timer"])

    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + \
        category + '" and type = "flow" ;'
    query_items = myquery.query_database(database, query_sql)
    for item in query_items:
        res_list["metrics_flow"].append(item['tag'])

    res = res + render_template('joint/body_div_line.html', name="metrics_flow")
    res = res+if_pages(res_list["metrics_flow"])

    return res

def run():
    slogging.start_log_monitor()
    app.run(host="0.0.0.0", port= 8080, debug=True)
    #app.run()

if __name__ == '__main__':
    run()
