
from multiprocessing import Lock
import common.config as cconfig
import pymysql.cursors
import time
import threading

class Store(str):
    def __init__(self, database=None):
        self.last_connect_time = int(time.time())
        self.lock = threading.Lock()
        
        print('当前数据库:{0},last_connect_time:{1}'.format(database,self.last_connect_time))
        self.tablecol = {
            "p2p": 'uniq_hash,msg_hash,msg_size,send_timestamp,src_ip,is_root,is_broadcast,recv_msg_cnt,recv_hash_cnt,vhost_recv_cnt,bypulled_cnt,packet_size,max_hop,avg_hop,max_delay,avg_delay,hop_num,recv_delay',
            "metrics_timer": 'send_timestamp,public_ip,category,tag,count,max_time,min_time,avg_time',
            "metrics_counter": 'send_timestamp,public_ip,category,tag,count,value',
            "metrics_timer": 'send_timestamp,public_ip,category,tag,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps',
            "ips_table":'public_ips',
            "tags_table":'category,tag,type',
            "vnode_status":'timestamp,public_ip,rec,zec,auditor,validator,archive,edge,fullnode',
        }
        self.db = pymysql.connect(**{
            'host': cconfig.DEFAULT_MYSQL_CONFIG['DB_HOST'],
            'port': cconfig.DEFAULT_MYSQL_CONFIG['DB_PORT'],
            'user': cconfig.DEFAULT_MYSQL_CONFIG['DB_USER'],
            'passwd': cconfig.DEFAULT_MYSQL_CONFIG['DB_PASS'],
            'db': "empty",
            'charset': 'UTF8MB4',
            # 'collate': 'utf8mb4_general_ci',
            'autocommit': True,
            'cursorclass': pymysql.cursors.DictCursor,
        })
        self.cursor = self.db.cursor()
        # 判断是否存在库
        self.cursor.execute('show databases like "{}"'.format(database))
        # 创建库
        if self.cursor.fetchone() is None:
            create_sql = 'CREATE DATABASE `{}` DEFAULT CHARACTER SET UTF8MB4 COLLATE utf8mb4_general_ci;'
            self.cursor.execute(create_sql.format(database))

            use_sql = 'USE `{}`;'
            self.cursor.execute(use_sql.format(database))

            # env_info:
            # env_info_sql = '\
            #     CREATE TABLE env_info(\
            #         k VARCHAR(100) DEFAULT "",\
            #         v VARCHAR(100) DEFAULT ""\
            #     )ENGINE = INNODB DEFAULT CHARSET = utf8;\
            #     INSERT INTO `env_info` (`k`,`v`) VALUES ("create_timestamp",NOW());'
            # self.cursor.execute(env_info_sql)

            # p2p gossip table
            create_p2p_table_sql = '\
            CREATE TABLE p2p(\
                uniq_hash BIGINT(20) unsigned NOT NULL,\
                msg_hash INT(10) unsigned NOT NULL,\
                msg_size INT(10) unsigned NOT NULL,\
                send_timestamp bigint(20) unsigned DEFAULT 0,\
                src_ip VARCHAR(20) DEFAULT "",\
                is_root INT(10) DEFAULT 0,\
                is_broadcast INT(10) DEFAULT 0,\
                recv_msg_cnt INT(10) DEFAULT 0,\
                recv_hash_cnt INT(10) DEFAULT 0,\
                vhost_recv_cnt INT(10) DEFAULT 0,\
                bypulled_cnt INT(10) DEFAULT 0,\
                packet_size INT(10) unsigned NOT NULL,\
                max_hop INT(10) DEFAULT 0,\
                avg_hop FLOAT(10) DEFAULT 0.0,\
                max_delay bigint(20) DEFAULT 0,\
                avg_delay FLOAT(10) DEFAULT 0.0,\
                hop_num VARCHAR(100) DEFAULT "",\
                recv_delay VARCHAR(100) DEFAULT "",\
                INDEX (send_timestamp, uniq_hash)\
            ) ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_table_sql)

            # metrics timer table
            # public_ip,category,tag,count,max_time,min_time,avg_time'
            create_metrics_timer_sql = '\
            CREATE TABLE metrics_timer(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(40) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count BIGINT(20) DEFAULT 0,\
                max_time BIGINT(20) DEFAULT 0,\
                min_time BIGINT(20) DEFAULT 0,\
                avg_time BIGINT(20) DEFAULT 0,\
                INDEX(category,tag,public_ip,send_timestamp)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_timer_sql)

            # metrics counter table
            create_metrics_counter_sql = '\
            CREATE TABLE metrics_counter(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(40) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count BIGINT(20) DEFAULT 0,\
                value BIGINT(20) DEFAULT 0,\
                INDEX(category,tag,public_ip,send_timestamp)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_counter_sql)

            # metrics flow table
            create_metrics_flow_sql = '\
            CREATE TABLE metrics_flow(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(40) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count BIGINT(20) DEFAULT 0,\
                max_flow BIGINT(20) DEFAULT 0,\
                min_flow BIGINT(20) DEFAULT 0,\
                sum_flow BIGINT(20) DEFAULT 0,\
                avg_flow BIGINT(20) DEFAULT 0,\
                tps_flow BIGINT(20) DEFAULT 0,\
                tps DOUBLE DEFAULT 0.00,\
                INDEX(category,tag,public_ip,send_timestamp)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_flow_sql)

            # ips_table
            create_ips_table_sql = '\
            CREATE TABLE ips_table(public_ips VARCHAR(40) DEFAULT "" PRIMARY KEY )ENGINE = InnoDB DEFAULT CHARSET=utf8;'
            self.cursor.execute(create_ips_table_sql)

            # tags_table
            create_tags_table_sql = '\
            CREATE TABLE tags_table (\
                category VARCHAR ( 30 ) DEFAULT "" NOT NULL,\
                tag VARCHAR ( 100 ) DEFAULT "" NOT NULL,\
                type VARCHAR ( 30 ) DEFAULT "" NOT NULL,\
                UNIQUE(type,category,tag)\
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_tags_table_sql)

            # vnode_status
            create_vnode_status_table_sql = '\
            CREATE TABLE vnode_status (\
                timestamp INT ( 10 ) DEFAULT 0 NOT NULL,\
                public_ip VARCHAR ( 40 ) DEFAULT "" NOT NULL,\
                rec INT ( 10 ) DEFAULT 0 NOT NULL,\
                zec INT ( 10 ) DEFAULT 0 NOT NULL,\
                auditor INT ( 10 ) DEFAULT 0 NOT NULL,\
                validator INT ( 10 ) DEFAULT 0 NOT NULL,\
                archive INT ( 10 ) DEFAULT 0 NOT NULL,\
                edge INT ( 10 ) DEFAULT 0 NOT NULL,\
                fullnode INT ( 10 ) DEFAULT 0 NOT NULL,\
            INDEX ( timestamp, public_ip ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_vnode_status_table_sql)

            # xsync_interval
            create_xsync_interval_table_sql = '\
            CREATE TABLE xsync_interval (\
                table_address VARCHAR ( 100 ) DEFAULT "",\
                sync_mod VARCHAR ( 20 ) DEFAULT "",\
                send_timestamp INT ( 10 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                self_min BIGINT ( 20 ) DEFAULT 0,\
                self_max BIGINT ( 20 ) DEFAULT 0,\
                peer_min BIGINT ( 20 ) DEFAULT 0,\
                peer_max BIGINT ( 20 ) DEFAULT 0,\
            INDEX ( table_address, sync_mod, send_timestamp ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_xsync_interval_table_sql)

            #kadinfo_root
            create_kadinfo_root_table_sql = '\
            CREATE TABLE kadinfo_root (\
                public_ip VARCHAR ( 40 ) DEFAULT "" NOT NULL,\
                node_id VARCHAR ( 100 ) DEFAULT "",\
                neighbours INT ( 10 ) DEFAULT 0,\
                last_update_time INT ( 10 ) DEFAULT 0,\
                UNIQUE ( public_ip, node_id ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_kadinfo_root_table_sql)

            #kadinfo_elect
            create_kadinfo_elect_table_sql = '\
            CREATE TABLE kadinfo_elect (\
                public_ip VARCHAR ( 40 ) DEFAULT "" NOT NULL,\
                node_id VARCHAR ( 100 ) DEFAULT "",\
                service_type VARCHAR ( 20 ) DEFAULT "",\
                node_size INT ( 10 ) DEFAULT 0,\
                height INT ( 10 ) DEFAULT 0,\
                unknown_node_size INT ( 10 ) DEFAULT 0,\
                last_update_time INT ( 10 ) DEFAULT 0,\
                UNIQUE ( public_ip, node_id, service_type, node_size, height) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_kadinfo_elect_table_sql)

            #p2p_raw_msg_info
            create_p2p_raw_msg_info_table_sql = '\
            CREATE TABLE p2p_raw_msg_info (\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                msg_hash BIGINT ( 20 ) NOT NULL,\
                timestamp BIGINT ( 20 ) DEFAULT 0,\
                type VARCHAR ( 20 ) DEFAULT 0,\
                src_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_node_id VARCHAR ( 100 ) DEFAULT "",\
                hop_num INT ( 10 ) DEFAULT 0,\
                msg_size INT ( 10 ) NOT NULL,\
                is_root INT ( 10 ) DEFAULT 0,\
                is_broadcast INT ( 10 ) DEFAULT 0,\
                INDEX ( msg_hash, public_ip ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_raw_msg_info_table_sql)

            
            #p2p_dump_msg_info
            create_p2p_dump_msg_info_table_sql = '\
            CREATE TABLE p2p_dump_msg_info (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                msg_hash BIGINT ( 20 ) NOT NULL,\
                src_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_node_id VARCHAR ( 100 ) DEFAULT "",\
                src_ip VARCHAR ( 40 ) DEFAULT "",\
                msg_size INT ( 10 ) NOT NULL,\
                is_root INT ( 10 ) DEFAULT 0,\
                is_broadcast INT ( 10 ) DEFAULT 0,\
                recv_node_cnt INT ( 10 ) DEFAULT 0,\
                recv_avg_delay FLOAT ( 10 ) DEFAULT 0.0,\
                avg_hop_num FLOAT ( 10 ) DEFAULT 0.0,\
                avg_packet_size FLOAT ( 10 ) DEFAULT 0.0,\
            INDEX ( msg_hash ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_dump_msg_info_table_sql)


            #p2p_test
            create_p2p_test_send_record_table_sql = '\
            CREATE TABLE p2ptest_send_record (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                msg_hash BIGINT ( 20 ) NOT NULL,\
                src_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_ip VARCHAR ( 40 ) DEFAULT "",\
                src_ip VARCHAR ( 40 ) DEFAULT "",\
                hop_num INT ( 10 ) DEFAULT 0,\
                msg_size INT ( 10 ) NOT NULL,\
                is_root INT ( 10 ) DEFAULT 0,\
                is_broadcast INT ( 10 ) DEFAULT 0,\
                INDEX ( msg_hash ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_test_send_record_table_sql)

            create_p2p_test_send_info_table_sql = '\
            CREATE TABLE p2ptest_send_info (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                msg_hash BIGINT ( 20 ) NOT NULL,\
                src_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_node_id VARCHAR ( 100 ) DEFAULT "",\
                src_ip VARCHAR ( 40 ) DEFAULT "",\
                hop_num INT ( 10 ) DEFAULT 0,\
                msg_size INT ( 10 ) NOT NULL,\
                is_root INT ( 10 ) DEFAULT 0,\
                is_broadcast INT ( 10 ) DEFAULT 0,\
                INDEX ( msg_hash ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_test_send_info_table_sql)

            create_p2p_test_recv_info_table_sql = '\
            CREATE TABLE p2ptest_recv_info (\
                recv_timestamp BIGINT ( 20 ) DEFAULT 0,\
                msg_hash BIGINT ( 20 ) NOT NULL,\
                src_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_node_id VARCHAR ( 100 ) DEFAULT "",\
                dst_ip VARCHAR ( 40 ) DEFAULT "",\
                hop_num INT ( 10 ) DEFAULT 0,\
                msg_size INT ( 10 ) DEFAULT 0,\
                packet_size INT ( 10 ) DEFAULT 0,\
                is_root INT ( 10 ) DEFAULT 0,\
                is_broadcast INT ( 10 ) DEFAULT 0,\
            INDEX ( msg_hash ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_p2p_test_recv_info_table_sql)

            #txpool_state
            create_txpool_state_table_sql = '\
            CREATE TABLE txpool_state (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                table_num BIGINT ( 20 ) DEFAULT 0,\
                unconfirm BIGINT ( 20 ) DEFAULT 0,\
                received_recv BIGINT ( 20 ) DEFAULT 0,\
                received_confirm BIGINT ( 20 ) DEFAULT 0,\
                pulled_recv BIGINT ( 20 ) DEFAULT 0,\
                pulled_confirm BIGINT ( 20 ) DEFAULT 0,\
            INDEX (public_ip) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_txpool_state_table_sql)
            #txpool_receipt
            create_txpool_receipt_table_sql = '\
            CREATE TABLE txpool_receipt (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                1clk BIGINT ( 20 ) DEFAULT 0,\
                2clk BIGINT ( 20 ) DEFAULT 0,\
                3clk BIGINT ( 20 ) DEFAULT 0,\
                4clk BIGINT ( 20 ) DEFAULT 0,\
                5clk BIGINT ( 20 ) DEFAULT 0,\
                6clk BIGINT ( 20 ) DEFAULT 0,\
                7to12clk BIGINT ( 20 ) DEFAULT 0,\
                13to30clk BIGINT ( 20 ) DEFAULT 0,\
                ex30clk BIGINT ( 20 ) DEFAULT 0,\
            INDEX (public_ip) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_txpool_receipt_table_sql)
            #txpool_cache
            create_txpool_cache_table_sql = '\
            CREATE TABLE txpool_cache (\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                send_cur BIGINT ( 20 ) DEFAULT 0,\
                recv_cur BIGINT ( 20 ) DEFAULT 0,\
                confirm_cur BIGINT ( 20 ) DEFAULT 0,\
                unconfirm_cur BIGINT ( 20 ) DEFAULT 0,\
                push_send_fail BIGINT ( 20 ) DEFAULT 0,\
                push_receipt_fail BIGINT ( 20 ) DEFAULT 0,\
                duplicate_cache BIGINT ( 20 ) DEFAULT 0,\
                repeat_cache BIGINT ( 20 ) DEFAULT 0,\
            INDEX (public_ip) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_txpool_cache_table_sql)

            #relayer gas
            create_relayer_gas_table_sql = '\
            CREATE TABLE relayer_gas (\
                seq_id INT ( 10 ) NOT NULL auto_increment,\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                count BIGINT ( 20 ) DEFAULT 0,\
                amount BIGINT ( 20 ) DEFAULT 0,\
                detail VARCHAR ( 80 ) DEFAULT 0,\
                PRIMARY KEY ( seq_id )\
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_relayer_gas_table_sql)

            #metrics_alarm
            create_metrics_alarm_table_sql = '\
            CREATE TABLE metrics_alarm (\
                seq_id INT ( 10 ) NOT NULL auto_increment,\
                send_timestamp BIGINT ( 20 ) DEFAULT 0,\
                public_ip VARCHAR ( 40 ) DEFAULT "",\
                category VARCHAR ( 30 ) DEFAULT "",\
                tag VARCHAR ( 100 ) DEFAULT "",\
                kv_content VARCHAR ( 1024 ) DEFAULT "",\
                PRIMARY KEY ( seq_id ),\
            INDEX ( public_ip ) \
            ) ENGINE = INNODB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_alarm_table_sql)

            # metrics array_counter
            create_metrics_array_counter_table_sql = '\
            CREATE TABLE metrics_array_counter(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(40) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count BIGINT(20) DEFAULT 0,\
                each_value VARCHAR(2048) DEFAULT "",\
                each_count VARCHAR(2048) DEFAULT "",\
                INDEX(category,tag,public_ip,send_timestamp)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_array_counter_table_sql)

            (self.cursor.close(), self.db.close(), self.__init__(database))

        self.db = pymysql.connect(**{
            'host': cconfig.DEFAULT_MYSQL_CONFIG['DB_HOST'],
            'port': cconfig.DEFAULT_MYSQL_CONFIG['DB_PORT'],
            'user': cconfig.DEFAULT_MYSQL_CONFIG['DB_USER'],
            'passwd': cconfig.DEFAULT_MYSQL_CONFIG['DB_PASS'],
            'db': database,
            'charset': 'UTF8MB4',
            # 'collate': 'utf8mb4_general_ci',
            'autocommit': True,
            'cursorclass': pymysql.cursors.DictCursor,
        })
        self.cursor = self.db.cursor()
        self.databasename = database

    def check_timeout(self):
        now_time = int(time.time())
        # print("now_time:{0}, last_connect_time:{1}".format(now_time,self.last_connect_time))
        if(now_time > self.last_connect_time and now_time-self.last_connect_time > 6*3600):
            self.reconnect()
        else:
            self.last_connect_time = now_time
        return

    def reconnect(self):
        self.cursor.close()
        self.db.close()
        self.db = pymysql.connect(**{
            'host': cconfig.DEFAULT_MYSQL_CONFIG['DB_HOST'],
            'port': cconfig.DEFAULT_MYSQL_CONFIG['DB_PORT'],
            'user': cconfig.DEFAULT_MYSQL_CONFIG['DB_USER'],
            'passwd': cconfig.DEFAULT_MYSQL_CONFIG['DB_PASS'],
            'db': self.databasename,
            'charset': 'UTF8MB4',
            'autocommit': True,
            'cursorclass': pymysql.cursors.DictCursor,
        })
        self.cursor = self.db.cursor()
        return

    def store_multi_insert(self, table, item: list):
        if not item:
            return ValueError('item error')
        self.check_timeout()

        size = len(item[0])
        keys = item[0].keys()
        safe_keys = ['`%s`' % k for k in keys]
        sql = 'INSERT INTO `%s`(%s) VALUES (%s)' % (table , ','.join(safe_keys),'%s' + ',%s' * (size - 1))
        val = tuple(tuple(v for _,v in each.items()) for each in item)
        last_id = self.cursor.executemany(sql, val)
        return last_id

    def store_insert(self, table, item: dict):
        if not item:
            return ValueError('item error')

        self.check_timeout()

        size = len(item)
        keys = item.keys()
        safe_keys = ['`%s`' % k for k in keys]
        sql = 'INSERT INTO `%s`(%s) VALUES(%s)' % (
            table, ','.join(safe_keys), '%s' + ',%s' * (size - 1))
        last_id = self.cursor.execute(sql, [item[key] for key in keys])
        return last_id
    
    def store_ignore_insert(self,table,item:dict):
        if not item:
            return ValueError('item error')
        
        self.check_timeout()

        size = len(item)
        keys = item.keys()
        safe_keys = ['`%s`' % k for k in keys]
        sql = 'INSERT IGNORE INTO `%s`(%s) VALUES(%s)' % (
            table, ','.join(safe_keys), '%s' + ',%s' * (size - 1))
        print(sql)
        last_id = self.cursor.execute(sql, [item[key] for key in keys])
        return last_id
    
    def store_insert_update(self,table,item:dict,update_item:list):
        if not item or not update_item:
            return ValueError('input item error')
        
        self.check_timeout()
        size = len(item)
        keys = item.keys()
        safe_keys = ['`%s`' % k for k in keys]
        sql = 'INSERT INTO `%s` ( %s ) VALUES ( %s )' % (table,','.join(safe_keys), '%s' + ',%s' * (size - 1))
        update_sql_list = ['`%s` = VALUES( `%s` )' % (k,k) for k in update_item]

        sql = sql + ' ON DUPLICATE KEY UPDATE '+ ','.join(update_sql_list)
        print(sql)
        last_id = self.cursor.execute(sql, [item[key] for key in keys])
        return last_id

    def query(self,sql):

        self.check_timeout()
        
        print(sql)
        self.lock.acquire()
        self.cursor.execute(sql)
        self.lock.release()
        return self.cursor.fetchall()
