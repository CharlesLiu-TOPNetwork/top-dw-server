
import common.config as cconfig
import pymysql.cursors


class Store(str):
    def __init__(self, database=None):
        print('当前数据库:', database)
        self.tablecol = {
            "p2p": 'uniq_hash,msg_hash,msg_size,send_timestamp,src_ip,is_root,is_broadcast,recv_msg_cnt,recv_hash_cnt,vhost_recv_cnt,bypulled_cnt,packet_size,max_hop,avg_hop,max_delay,avg_delay,hop_num,recv_delay',
            "metrics_timer": 'send_timestamp,public_ip,category,tag,count,max_time,min_time,avg_time',
            "metrics_counter": 'send_timestamp,public_ip,category,tag,count,value',
            "metrics_timer": 'send_timestamp,public_ip,category,tag,count,max_flow,min_flow,sum_flow,avg_flow,tps_flow,tps'
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
            create_sql = 'CREATE DATABASE {} DEFAULT CHARACTER SET UTF8MB4 COLLATE utf8mb4_general_ci;'
            self.cursor.execute(create_sql.format(database))

            use_sql = 'USE {};'
            self.cursor.execute(use_sql.format(database))

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
                public_ip VARCHAR(20) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count INT(10) DEFAULT 0,\
                max_time INT(10) DEFAULT 0,\
                min_time INT(10) DEFAULT 0,\
                avg_time INT(10) DEFAULT 0,\
                INDEX(send_timestamp,public_ip)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_timer_sql)

            # metrics counter table
            create_metrics_counter_sql = '\
            CREATE TABLE metrics_counter(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(20) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count INT(10) DEFAULT 0,\
                value INT(10) DEFAULT 0,\
                INDEX(send_timestamp,public_ip)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_counter_sql)

            # metrics flow table
            create_metrics_flow_sql = '\
            CREATE TABLE metrics_flow(\
                send_timestamp INT(10) DEFAULT 0,\
                public_ip VARCHAR(20) DEFAULT "",\
                category VARCHAR(30) DEFAULT "",\
                tag VARCHAR(100) DEFAULT "",\
                count INT(10) DEFAULT 0,\
                max_flow INT(10) DEFAULT 0,\
                min_flow INT(10) DEFAULT 0,\
                sum_flow INT(10) DEFAULT 0,\
                avg_flow INT(10) DEFAULT 0,\
                tps_flow INT(10) DEFAULT 0,\
                tps DOUBLE DEFAULT 0.00,\
                INDEX(send_timestamp,public_ip)\
            )ENGINE = InnoDB DEFAULT CHARSET = utf8;'
            self.cursor.execute(create_metrics_flow_sql)


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

    def store_insert(self, table, item: dict):
        if not item:
            return ValueError('item error')

        size = len(item)
        keys = item.keys()
        safe_keys = ['`%s`' % k for k in keys]
        sql = 'INSERT INTO `%s`(%s) VALUES(%s)' % (
            table, ','.join(safe_keys), '%s' + ',%s' * (size - 1))
        print(sql)
        last_id = self.cursor.execute(sql, [item[key] for key in keys])
        return last_id
