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
import common.config as config

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

# ![for_QA][raw_data_api][help_function]
def check_db_exist(db_name: str) -> bool:
    # check db exist
    database_list = [k['name'] for k in database_time()]
    if db_name not in database_list:
        return False
    return True

# ![for_QA][raw_data_api][help_page]
@app.route('/dw-api/help',methods=['GET'])
@app.route('/dw-api/help/',methods=['GET'])
def raw_query_help():
    return render_template('query_center/raw_query_help.html')

# ![for_QA][raw_data_api]
@app.route('/dw-api/database',methods=['GET'])
@app.route('/dw-api/database/',methods=['GET'])
def raw_query_database():
    database_list = database_time()
    database_list = [d['name'] for d in database_list]
    return jsonify(database_list)

# ![for_QA][raw_data_api]
@app.route('/dw-api/category',methods=['GET'])
@app.route('/dw-api/category/',methods=['GET'])
def raw_query_category():
    env = request.args.get('env') or None
    type = request.args.get('type') or None
    
    if not env:
        return "plz set env"
    if not check_db_exist(env):
        return "env not exist"
    if type and type not in ['array_counter','alarm','counter','timer','flow']:
        return 'type should be one of [array_counter / alarm / counter / timer / flow]'
    
    query_sql = 'SELECT DISTINCT category FROM tags_table '
    if type :
        query_sql = query_sql + 'WHERE type = "' + type + '" ;'
    else:
        query_sql = query_sql + ';'
    query_items = myquery.query_database(env,query_sql)
    res_list = []
    for item in query_items:
        res_list.append(item['category'])
    
    return jsonify(res_list)


# ![for_QA][raw_data_api]
@app.route('/dw-api/tag',methods=['GET'])
@app.route('/dw-api/tag/',methods=['GET'])
def raw_query_tag():
    env = request.args.get('env') or None
    category = request.args.get('category') or None
    type = request.args.get('type') or None
    
    if not env:
        return "plz set env"
    if not check_db_exist(env):
        return "env not exist"
    if not category:
        return "plz set category"
    if type not in ['array_counter','alarm','counter','timer','flow']:
        return 'plz set type [array_counter / alarm / counter / timer / flow]'

    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + category + '" and type = "' + type + '" ;'
    query_items = myquery.query_database(env,query_sql)
    # print(query_sql,query_items)
    res_list = []
    for item in query_items:
        res_list.append(item['tag'])
    
    return jsonify(res_list)


# ![for_QA][raw_data_api]
@app.route('/dw-api/txpool',methods=['GET'])
@app.route('/dw-api/txpool/',methods=['GET'])
def raw_query_txpool():
    env = request.args.get('env') or None
    ip = request.args.get('ip') or None
    type = request.args.get('type') or None

    if not env:
        return "plz set env"
    if not check_db_exist(env):
        return "env not exist"
    if not ip:
        return "plz set ip"
    if not type or type not in ['state', 'receipt', 'cache']:
        return "plz set type [ state / receipt / cache ]"

    sql = ''
    # sql_template = 'SELECT * FROM (( SELECT * FROM txpool_'+ type +' {0} ORDER BY send_timestamp DESC ) AS tmp ) GROUP BY public_ip;'

    if ip == 'all' :
        sql = 'SELECT * FROM (( SELECT * FROM txpool_'+ type +' {0} ORDER BY send_timestamp DESC ) AS tmp ) GROUP BY public_ip;'.format('')
    else:
        # check ip exist
        query_ip_sql = 'SELECT public_ips FROM ips_table;'
        query_items = myquery.query_database(env, query_ip_sql)
        ip_list = []
        for item in query_items:
            ip_list.append(item['public_ips'])
        if ip not in ip_list:
            return "ip {0} not exist in {1}".format(ip, env)
        sql = 'SELECT * FROM txpool_'+ type +' {0} ORDER BY send_timestamp DESC;'.format('WHERE public_ip = "'+ ip +'"')
    
    # print(sql)
    
    return jsonify(myquery.query_database(env,sql)) 



# ![for_QA][inner_logcal][raw_data_api]
def raw_query_metrics_all_ip(env,type,category,tag):
    if type == "counter":
        sql = 'SELECT public_ip, send_timestamp, count, value FROM (( SELECT * FROM metrics_counter WHERE category = "{0}" AND tag = "{1}" ORDER BY send_timestamp DESC ) AS tmp ) GROUP BY	public_ip;'.format(category,tag)
    elif type == "timer":
        sql = 'SELECT public_ip, send_timestamp, count, max_time, min_time, avg_time FROM (( SELECT * FROM metrics_timer WHERE category = "{0}" AND tag = "{1}" ORDER BY send_timestamp DESC ) AS tmp ) GROUP BY public_ip;'.format(category,tag)
    elif type == "flow":
        sql = 'SELECT public_ip, send_timestamp, count, max_flow, min_flow, sum_flow, avg_flow, tps_flow, tps FROM (( SELECT * FROM metrics_flow WHERE category = "{0}" AND tag = "{1}" ORDER BY send_timestamp DESC ) AS tmp ) GROUP BY public_ip;'.format(category,tag)
    else:
        return 'wrong type for now'
    
    return jsonify(myquery.query_database(env,sql))

# ![for_QA][raw_data_api]
@app.route('/dw-api/metrics',methods=['GET'])
@app.route('/dw-api/metrics/',methods=['GET'])
# @auth.login_required
def raw_query_metrics():
    env = request.args.get('env') or None
    ip = request.args.get('ip') or None
    type = request.args.get('type') or None
    category = request.args.get('category') or None
    tag = request.args.get('tag') or None
    latest = request.args.get('latest') or None

    if not env:
        return "plz set env"
    if not check_db_exist(env):
        return "env not exist"
    if not ip:
        return "plz set ip"
    if not type or type not in ['counter', 'timer', 'flow']:
        return "plz set type [ counter / timer / flow ]"
    if not category or not tag:
        return "plz set category && tag"
    if latest and latest not in ['true','false']:
        return "plz set latest [ true(default) / false ]"

    # check category_tag exist
    query_sql = 'SELECT DISTINCT tag FROM tags_table where category = "' + category + '" and type = "' + type + '" ;'
    query_items = myquery.query_database(env, query_sql)
    tag_list = []
    for item in query_items:
        tag_list.append(item['tag'])
    if tag not in tag_list:
        return "category: [ {0} ] tag: [ {1} ] not exist in db [ {2} ]".format(category, tag, env)

    # check ip exist
    if ip == 'all' :
        return raw_query_metrics_all_ip(env,type,category,tag)
    query_ip_sql = 'SELECT public_ips FROM ips_table;'
    query_items = myquery.query_database(env, query_ip_sql)
    ip_list = []
    for item in query_items:
        ip_list.append(item['public_ips'])
    if ip not in ip_list:
        return "ip {0} not exist in {1}".format(ip, env)

    sql = ''

    if type == "counter":
        #SELECT send_timestamp,count,value FROM metrics_counter WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "recv_msg";
        sql = 'SELECT send_timestamp,count,value FROM metrics_counter WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}" ORDER BY send_timestamp '.format(
            ip, category, tag)
    elif type == "timer":
        #SELECT send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "handle_data_filter";
        sql = 'SELECT send_timestamp,count,max_time,min_time,avg_time FROM metrics_timer WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}" ORDER BY send_timestamp '.format(
            ip, category, tag)
    elif type == "flow":
        #SELECT send_timestamp,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE public_ip = "192.168.181.128" AND category = "vhost" AND tag = "handle_data_ready_called";
        sql = 'SELECT send_timestamp,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps FROM metrics_flow WHERE public_ip = "{0}" AND category = "{1}" AND tag = "{2}" ORDER BY send_timestamp '.format(
            ip, category, tag)
    else:
        return 'wrong type for now'
    
    if latest and latest == 'false':
        sql = sql + ';'
    else:
        sql = sql + 'DESC LIMIT 1 ;'

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
# ![function] used by other apis, return an [category - tag - type:array_counter]'s all nodes' metrics data (one full picture)
def query_array_counter(database,category,tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,each_value,each_count FROM metrics_array_counter WHERE category = "' + \
        category+'" AND tag = "'+tag + '" ORDER BY public_ip,send_timestamp;'
    query_items = myquery.query_database(database,query_sql)

    res_item = {}
    x_list = []
    data_lists = {
        'count':{},
        'sum_value':{},
    }
    # print(query_items)
    if not query_items:
        return "no data with {0} {1} {2} {3}".format(database,category,tag)
    size = len(query_items[0]['each_value'][1:-1].split(","))
    # print(size)
    for i in range(0,size) : 
        data_lists['count_'+str(i)]={}
        data_lists['value_'+str(i)]={}

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
        each_value = item['each_value'][1:-1].split(",")
        res_item[ip][ts]['sum_value'] = sum([int(_e) for _e in each_value])
        each_count = item['each_count'][1:-1].split(",")
        for i in range(0,size):
            res_item[ip][ts]['count_'+str(i)] = each_count[i]
            res_item[ip][ts]['value_'+str(i)] = each_value[i]
    
    # print(res_item)

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
    res = res + render_template('joint/body_center_line_chart_for_pair_metrics_tag.html.j2', 
                                name = "sum_data",
                                name_1="sum_count", 
                                name_2="sum_value", 
                                data_list_1=format_data_list_to_str(data_lists['count']), 
                                data_list_2=format_data_list_to_str(data_lists['sum_value']), 
                                x_list=format_timestamp_list(x_list), 
                                append_info='[' + database + ']' + category + '_' + tag)
    
    for i in range(0,size) : 
        res = res + render_template('joint/body_center_line_chart_for_pair_metrics_tag.html.j2', 
                                name = "index_"+str(i)+"_data",
                                name_1='count_'+str(i), 
                                name_2='value_'+str(i), 
                                data_list_1=format_data_list_to_str(data_lists['count_'+str(i)]), 
                                data_list_2=format_data_list_to_str(data_lists['value_'+str(i)]), 
                                x_list=format_timestamp_list(x_list), 
                                append_info='[' + database + ']' + category + '_' + tag)


    # for _key, data_list in data_lists.items():
    #     res = res + render_template('joint/body_div_line.html', name=_key)
    #     res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag.html.j2',
    #                                 name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag)
    return res


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
        'rate': {},
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
        if item['count'] == 0 and item['value'] == 0:
            res_item[ip][ts]['rate'] = 1
        elif item['count'] == 0:
            res_item[ip][ts]['rate'] = 0
        else:
            res_item[ip][ts]['rate'] = round(item['value']/item['count'],3)


    x_list.sort()

    for _key, data_list in data_lists.items():
        for _ip, _list in data_list.items():
            for ts in x_list:
                if ts in res_item[_ip]:
                    _list.append(res_item[_ip][ts][_key])
                else:
                    _list.append(None)

    # print(data_lists)
    res = render_template('joint/body_div_line.html', name=category+'_'+tag)
    chart_index = 0
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name='')
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag_with_tps.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag, index = chart_index)
        chart_index = chart_index + 1
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
    res = render_template('joint/body_div_line.html', name=category+'_'+tag)
    chart_index = 0
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name='')
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag_with_tps.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag, index = chart_index)
        chart_index = chart_index + 1
    return res

# ![function] used by other apis, return an [category - tag - type:timer]'s all nodes' metrics data (one full picture)
def query_timer(database, category, tag):
    query_sql = 'SELECT public_ip,send_timestamp,count,max_time,min_time,avg_time,(count * avg_time) as sum_time FROM metrics_timer WHERE category = "' + \
        category + '" AND tag = "' + tag + '" ORDER BY public_ip,send_timestamp;'
    query_items = myquery.query_database(database, query_sql)

    res_item = {}
    x_list = []
    data_lists = {
        'count': {},
        'max_time': {},
        'min_time': {},
        'avg_time': {},
        'sum_time': {},
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
        res_item[ip][ts]['sum_time'] = item['sum_time']

    x_list.sort()

    for _key, data_list in data_lists.items():
        for _ip, _list in data_list.items():
            for ts in x_list:
                if ts in res_item[_ip]:
                    _list.append(res_item[_ip][ts][_key])
                else:
                    _list.append(None)

    # print(data_lists)
    res = render_template('joint/body_div_line.html', name=category+'_'+tag)
    chart_index = 0
    for _key, data_list in data_lists.items():
        res = res + render_template('joint/body_div_line.html', name='')
        res = res + render_template('joint/body_big_line_chart_for_one_metrics_tag_with_tps.html.j2',
                                    name=_key, data_list=format_data_list_to_str(data_list), x_list=format_timestamp_list(x_list), append_info = '[' + database + ']' + category + '_' + tag, index = chart_index)
        chart_index = chart_index + 1
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
    elif type == 'array_counter':
        return query_array_counter(database, category, tag)
    else:
        return "query_category_tag_metrics"  


# ![api] return an [ip - category]'s all metrics data (a long long div)
@app.route('/query_ip_category_metrics',methods=['GET'])
@app.route('/query_ip_category_metrics/',methods=['GET'])
def query_ip_category_metrics():
    database = request.args.get('database') or None
    ip = request.args.get('public_ip') or None
    category = request.args.get('category') or None

    chart_index = 0

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
                    'rate':[],
                    # 'value_tps':[],
                },
            }
        # last_ts = res_item[tag]['list_x'][-1] if len(res_item[tag]['list_x']) else item['send_timestamp']
        # last_value = res_item[tag]['value_series']['value'][-1] if len(res_item[tag]['value_series']['value']) else item['value']
        
        ts = item['send_timestamp']
        res_item[tag]['list_x'].append(ts)
        res_item[tag]['value_series']['count'].append(item['count'])
        res_item[tag]['value_series']['value'].append(item['value'])
        if item['value'] == 0 and item['count'] == 0:
            res_item[tag]['value_series']['rate'].append(1)
        elif item['value']==0:
            res_item[tag]['value_series']['rate'].append(0)
        else:
            res_item[tag]['value_series']['rate'].append(round(item['value']/item['count'],3))
        # res_item[tag]['value_series']['value_tps'].append(0 if last_ts == ts else (item['value']-last_value)/(ts-last_ts))

    res = render_template('joint/body_div_line.html', name = "metrics_counter")
    for _tag,_value in res_item.items():
        res = res + render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip_with_tps.html.j2', name=_tag,index = chart_index,
                                    value_series=_value['value_series'], list_x=format_timestamp_list(_value['list_x']), append_info = '[' + database + '] ' + ip + ' ' + category)
        chart_index = chart_index + 1


    res = res + render_template('joint/body_div_line.html', name = "metrics_timer")
    # metrics_timer:
    query_sql = 'SELECT tag,send_timestamp,count,max_time,min_time,avg_time,(count * avg_time) as sum_time FROM metrics_timer WHERE public_ip = "{0}" AND category = "{1}" ORDER BY tag,send_timestamp;'.format(ip, category)
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
                    'sum_time':[],
                },
            }
        ts = item['send_timestamp']
        res_item[tag]['list_x'].append(ts)
        res_item[tag]['value_series']['count'].append(item['count'])
        res_item[tag]['value_series']['max_time'].append(item['max_time'])
        res_item[tag]['value_series']['min_time'].append(item['min_time'])
        res_item[tag]['value_series']['avg_time'].append(item['avg_time'])
        res_item[tag]['value_series']['sum_time'].append(item['sum_time'])

    for _tag,_value in res_item.items():
        res = res + render_template('joint/body_small_line_chart_for_one_metrics_tag_one_ip.html.j2', name=_tag,
                                    value_series=_value['value_series'], list_x=format_timestamp_list(_value['list_x']), append_info = '[' + database + ']' + ip + ' ' + category)
    
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
                                    value_series=_value['value_series'], list_x = format_timestamp_list(_value['list_x']), append_info = '[' + database + ']' + ip + ' ' + category)


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
        x_str_list = []
        for i,x in enumerate(_list):
            if x is None:
                x_str_list.append('')
            elif i != 0 and x == 0 and _list[i-1] == 0 and i != len(_list)-1:
                x_str_list.append('')
            else:
                x_str_list.append(str(x))
        res_list_str = ",".join(x_str_list)
            
        # res_list_str = ",".join([str(x) if x else ' ' for x in _list])
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

#![help_tools] convert a [list] into a [str]
def format_txpool_data_list_to_str(tag_list:list,input_map:dict):
    res_map = {}
    for ts,item in input_map.items():
        format_ts = time.strftime(format_regex, time.localtime(ts))
        res_map[format_ts] = {
            'value':"",
            'sum_pie':"",
        }
        for _tag in tag_list:
            res_map[format_ts]['value'] +=str(input_map[ts][_tag])+","
            if input_map[ts][_tag]!=0:
                res_map[format_ts]['sum_pie'] += "{name:'"+_tag + "',value:" + str(input_map[ts][_tag]) +"},"
            else:
                res_map[format_ts]['sum_pie'] += "{name:'"+_tag + "',value:null},"
    return res_map

#![help_tools] convert a [list] into a [str]
def format_compare_txpool_data_list_to_str(tag_list:list,input_map:dict):
    res_map = {}
    for ts,item in input_map.items():
        format_ts = time.strftime(format_regex, time.localtime(ts))
        res_map[format_ts] = {
            'n1_value':"",
            'n2_value':"",
            'sum_pie':"",
        }
        for _tag in tag_list:
            res_map[format_ts]['n1_value'] +=str(input_map[ts][_tag]['n1'])+","
            res_map[format_ts]['n2_value'] +=str(input_map[ts][_tag]['n2'])+","
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

# ![page] query txpool real_time metrics
@app.route('/xtxpool',methods=['GET'])
@app.route('/xtxpool/',methods=['GET'])
def xtxpool():
    return render_template('query_center/special_packet_xtxpool.html.j2',database_list = database_time())

# ![page] query metrics alarm
@app.route('/metrics_alarm',methods=['GET'])
@app.route('/metrics_alarm/',methods=['GET'])
def metrics_alarm():
    return render_template('query_center/metrics_alarm.html.j2',database_list = database_time())

# ![page][center]
@app.route('/center',methods=['GET'])
@app.route('/center/',methods=['GET'])
def center_page():
    return render_template('query_center/center.html.j2',title = config.ADDRESS_USAGE)


# ![api] query_alarm_page: used by metrics_alarm.html. query button return a table div.
@app.route('/query_alarm_page',methods=['GET'])
@app.route('/query_alarm_page/',methods=['GET'])
def query_alarm_page():
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    category = request.args.get('category') or None
    
    query_sql = "select count(seq_id) as res_cnt from metrics_alarm "
    if public_ip != "all_ip" and category !="all_category":
        query_sql = query_sql + 'where public_ip="'+public_ip+'" and '+ 'category="'+category+'" '  
    elif public_ip != "all_ip":
        query_sql = query_sql + 'where public_ip="'+public_ip+'" '
    elif category != "all_category":
        query_sql = query_sql + 'where category="'+category+'" '    
    # print(query_sql)
    query_items = myquery.query_database(database,query_sql)
    if not query_items[0]['res_cnt']:
        return "no alarm with {0} {1} {2}".format(database,public_ip,category)
    return render_template('joint/body_table_metrics_alarm.html.j2', max_seq=query_items[0]['res_cnt'], database=database, public_ip=public_ip, category=category)

# ![api] query_alarm_data: used by more data in body_table_metrics_alarm.html.j2
@app.route('/query_alarm_data',methods=['GET'])
@app.route('/query_alarm_data/',methods=['GET'])
def query_alarm_data():
    database = request.args.get('database') or None
    category = request.args.get('category') or None
    public_ip = request.args.get('public_ip') or None
    begin_seq_id = request.args.get('begin_seq_id') or None
    
    query_sql = "select * from metrics_alarm "
    if public_ip != "all_ip" and category !="all_category":
        query_sql = query_sql + 'where public_ip="'+public_ip+'" and '+ 'category="'+category+'" '  
    elif public_ip != "all_ip":
        query_sql = query_sql + 'where public_ip="'+public_ip+'" '
    elif category != "all_category":
        query_sql = query_sql + 'where category="'+category+'" ' 
    query_sql = query_sql + "limit {0},10".format(begin_seq_id)
    # print(query_sql)
    # query_sql = "select * from metrics_alarm limit {0},10".format(begin_seq_id)
    query_items = myquery.query_database(database,query_sql)
    for item in query_items:
        item['send_timestamp'] = time.strftime(format_regex, time.localtime(item['send_timestamp']))
    # print(query_items)
    # print(jsonify(query_items))
    return jsonify(query_items)

txpool_cache_item_list = ['send_cur','recv_cur','confirm_cur','unconfirm_cur','push_send_fail','push_receipt_fail','duplicate_cache','repeat_cache']
txpool_state_item_list = ['table_num','unconfirm','received_recv','received_confirm','pulled_recv','pulled_confirm']
txpool_receipt_item_list = ['1clk','2clk','3clk','4clk','5clk','6clk','7to12clk','13to30clk','ex30clk']

# ![api] query_txpool_table
@app.route('/query_txpool_table',methods=['GET'])
@app.route('/query_txpool_table/',methods=['GET'])
def query_txpool_table():
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    table_name = request.args.get('table_name') or None
    
    res_page = ""
    query_sql = ""
    tag_list = []
    if table_name == 'txpool_cache':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_cache` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_cache_item_list), public_ip)
        tag_list = txpool_cache_item_list
    elif table_name == 'txpool_state':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_state` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_state_item_list), public_ip)
        tag_list = txpool_state_item_list
    elif table_name == 'txpool_receipt':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_receipt` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_receipt_item_list), public_ip)
        tag_list = txpool_receipt_item_list
    
    query_items = myquery.query_database(database,query_sql)
    if not query_items:
        res_page += "None data with " + table_name
    else:
        res_map = {}
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            if ts not in res_map:
                res_map[ts]={}
            if ts not in ts_list:
                ts_list.append(ts)
            for _tag in tag_list:
                res_map[ts][_tag] = item[_tag]
        ts_list.sort()
        res_page += render_template('joint/body_big_line_chart_for_txpool.html.j2',name = public_ip + " "+ table_name,ts_list = format_timestamp_list(ts_list),tag_list = tag_list,res_map = format_txpool_data_list_to_str(tag_list,res_map))

    return res_page

# ![api] query_txpool_table_compared
@app.route('/query_txpool_table_compared',methods=['GET'])
@app.route('/query_txpool_table_compared/',methods=['GET'])
def query_txpool_table_compared():
    database = request.args.get('database') or None
    public_ip = request.args.get('public_ip') or None
    table_name = request.args.get('table_name') or None
    o_public_ip = request.args.get('o_public_ip') or None
    
    res_page = ""
    query_sql = ""
    o_query_sql = ""
    tag_list = []
    if table_name == 'txpool_cache':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_cache` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_cache_item_list), public_ip)
        o_query_sql = 'SELECT send_timestamp,{0} FROM `txpool_cache` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_cache_item_list), o_public_ip)
        tag_list = txpool_cache_item_list
    elif table_name == 'txpool_state':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_state` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_state_item_list), public_ip)
        o_query_sql = 'SELECT send_timestamp,{0} FROM `txpool_state` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_state_item_list), o_public_ip)
        tag_list = txpool_state_item_list
    elif table_name == 'txpool_receipt':
        query_sql = 'SELECT send_timestamp,{0} FROM `txpool_receipt` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_receipt_item_list), public_ip)
        o_query_sql = 'SELECT send_timestamp,{0} FROM `txpool_receipt` WHERE public_ip = "{1}";'.format(
            ','.join(txpool_receipt_item_list), o_public_ip)
        tag_list = txpool_receipt_item_list
    query_items = myquery.query_database(database,query_sql)
    if not query_items:
        res_page += "None data with " + public_ip + table_name
    else:
        res_map = {}
        ts_list = []
        for item in query_items:
            ts = item['send_timestamp']
            if ts not in res_map:
                res_map[ts]={}
                for _tag in tag_list:
                    res_map[ts][_tag] = {
                        'n1':'',
                        'n2':'',
                    }
            if ts not in ts_list:
                ts_list.append(ts)
            for _tag in tag_list:
                res_map[ts][_tag]['n1'] = item[_tag]
        
        # o_public_ip
        query_items = myquery.query_database(database,o_query_sql)

        if not query_items:
            res_page += "None data with " + o_public_ip + " " + table_name
        else:
            for item in query_items:
                ts = item['send_timestamp']
                if ts not in res_map:
                    res_map[ts]={}
                    for _tag in tag_list:
                        res_map[ts][_tag] = {
                            'n1':'',
                            'n2':'',
                        }
                if ts not in ts_list:
                    ts_list.append(ts)
                for _tag in tag_list:
                    res_map[ts][_tag]['n2'] = item[_tag]

        ts_list.sort()
        res_page += render_template('joint/body_big_line_chart_for_compare_txpool.html.j2',name = public_ip + " "+ table_name,ts_list = format_timestamp_list(ts_list),tag_list = tag_list,res_map = format_compare_txpool_data_list_to_str(tag_list,res_map),p_ip = public_ip,o_ip = o_public_ip)

    return res_page

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
@app.route('/tmp_test_page',methods=['GET'])
@app.route('/tmp_test_page/',methods=['GET'])
def tmp_test_page():

    return render_template('tmp.html')

# ![api] set database manager info
@app.route('/update_db_reserve',methods=['GET'])
@app.route('/update_db_reserve/',methods=['GET'])
def update_db_reserve():
    database = request.args.get('database') or None
    val = request.args.get('val') or None
    query_sql = 'UPDATE `db_setting` SET `reserve` ="{0}" WHERE db_name = "{1}" ;'.format(val,database)
    myquery.query_database('empty',query_sql)
    print(query_sql)
    return "ok"

# ![api] get database manager info
@app.route('/query_db_manager_info',methods=['GET'])
@app.route('/query_db_manager_info/',methods=['GET'])
def query_db_manager_info():
    query_sql = "select * from db_setting"
    query_items = myquery.query_database('empty',query_sql)
    return jsonify(query_items)

# ![page] manager database info
@app.route('/db_manager',methods=['GET'])
@app.route('/db_manager/',methods=['GET'])
def db_manager():
    # query_sql = "select * from db_setting"
    # query_items = myquery.query_database('empty',query_sql)
    return render_template('query_center/db_manager.html.j2')

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
        'fullnode': [],
    }
    new_status = False
    for item in query_items:
        ts = item['timestamp']
        list_x.append(ts)
        if new_status == False and (item['rec']<0 or item['zec']<0 or item['archive']<0 or item['edge']<0 or (item['auditor'] !=4 and item['auditor'] !=0)  or item['validator'] > 3):
            new_status = True
        res_item['rec'].append(item['rec'])
        res_item['zec'].append(item['zec'])
        res_item['auditor'].append(item['auditor'])
        res_item['validator'].append(item['validator'])
        res_item['archive'].append(item['archive'])
        res_item['edge'].append(item['edge'])
        res_item['fullnode'].append(0) # todo

    if new_status:
        res = render_template('joint/body_center_line_chart_for_vnode_status2.html.j2',
                          name='vnode_status', value_series=res_item, list_x=format_timestamp_list(list_x),append_info = '[' + database + '] ' + public_ip)
    else:
        res = render_template('joint/body_center_line_chart_for_vnode_status.html.j2',
                          name='vnode_status', value_series=res_item, list_x=format_timestamp_list(list_x),append_info = '[' + database + '] ' + public_ip)
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

# ![api] query one database category with certain type
@app.route('/query_categorys_with_type',methods=['GET'])
@app.route('/query_categorys_with_type/',methods=['GET'])
def query_categorys_with_type():
    database = request.args.get('database') or None
    type = request.args.get('type') or None
    query_sql = 'SELECT DISTINCT category FROM tags_table where type= "{0}";'.format(type)
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
    # app.run(host="0.0.0.0", port= 8080, debug=True)
    app.run(host="0.0.0.0", port= 8080)
    #app.run()

if __name__ == '__main__':
    run()
