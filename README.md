### TOP-DW-server


### Usage
1. git,wget, pull project
    ``` shell
    yum install -y git wget
    git clone https://github.com/CharlesLiu-TOPNetwork/top-dw-server.git
    cd top-dw-server
    ```
2. vvlinux:
    ``` shell
    pip3 install virtualenv
    virtualenv  -p /usr/bin/python3 vvlinuxs
    source  vvlinux/bin/activate
    pip3 install -r requirements.txt
    ```
3. nginx
    ``` shell
    yum -y install gcc gcc-c++ make libtool zlib zlib-devel openssl openssl-devel pcre pcre-devel

    mkdir /root/temp -p && cd /root/temp
    wget http://nginx.org/download/nginx-1.14.2.tar.gz
    tar zxvf nginx-1.14.2.tar.gz
    cd nginx-1.14.2
    ./configure --with-http_stub_status_module --with-http_ssl_module --with-pcre
    make -j4 && make install
    ```

    > nginx path prefix: "/usr/local/nginx"
    nginx binary file: "/usr/local/nginx/sbin/nginx"
    nginx modules path: "/usr/local/nginx/modules"
    nginx configuration prefix: "/usr/local/nginx/conf"
    nginx configuration file: "/usr/local/nginx/conf/nginx.conf"
    nginx pid file: "/usr/local/nginx/logs/nginx.pid"
    nginx error log file: "/usr/local/nginx/logs/error.log"
    nginx http access log file: "/usr/local/nginx/logs/access.log"
    nginx http client request body temporary files: "client_body_temp"
    nginx http proxy temporary files: "proxy_temp"
    nginx http fastcgi temporary files: "fastcgi_temp"
    nginx http uwsgi temporary files: "uwsgi_temp"
    nginx http scgi temporary files: "scgi_temp"

    changd nginx.conf.
    `./sbin/nginx -c conf/nginx.conf`

4. redis
    ``` shell
    yum install redis -y
    vi /etc/redis.conf
    # 端口 bind 0.0.0.0;
    # 480行可以修改redis密码 requirepass yourpasswd;
    redis-server [config_path] &
    redis-cli -a yourpasswd 验证启动成功
    ```

5. mysql
- clear mariadb
    ``` shell
    rpm -qa | grep mariadb
    rpm -e mariadb --nodeps
    rpm -e mariadb-libs --nodeps
    ```
- install mysql 5.6.51
    ``` shell
    wget https://downloads.mysql.com/archives/get/p/23/file/MySQL-5.6.51-1.el7.x86_64.rpm-bundle.tar
    tar xvf MySQL-5.6.51-1.el7.x86_64.rpm-bundle.tar
    yum install -y perl-Data-Dumper net-tools libaio
    rpm -ivh MySQL-server-5.6.51-1.el7.x86_64.rpm
    ```
    > A RANDOM PASSWORD HAS BEEN SET FOR THE MySQL root USER !
    You will find that password in '/root/.mysql_secret'.
    You must change that password on your first connect,
    no other statement but 'SET PASSWORD' will be accepted.
    See the manual for the semantics of the 'password expired' flag.
    Also, the account for the anonymous user has been removed.
    In addition, you can run:
    /usr/bin/mysql_secure_installation
    which will also give you the option of removing the test database.
    This is strongly recommended for production servers.
    See the manual for more instructions.
    Please report any problems at http://bugs.mysql.com/
    The latest information about MySQL is available on the web at
    http://www.mysql.com
    Support MySQL by buying support/licenses at http://shop.mysql.com
    New default config file was created as /usr/my.cnf and
    will be used by default by the server when you start it.
    You may edit this file to change server settings

    ``` shell
    rpm -ivh MySQL-client-5.6.51-1.el7.x86_64.rpm
    ```

- start mysql
    ``` shell
    systemctl start mysql
    systemctl status mysql
    ```

- change pswd
    ``` shell
    cat /root/.mysql_secret | grep password
    # The random password set for the root user at Wed Sep 15 04:21:41 2021 (local time): 0KDf2utLbFD7Txs4


    mysql -u root -p
    0KDf2utLbFD7Txs4

    SET PASSWORD = PASSWORD('123456');
    ```


6. 清理日志定时任务：
    `crontab -e`
    ``` shell
    crontab -l
    0 */6 * * *  ls /var/log/gunicorn*.log |xargs truncate -s 0
    0 */6 * * *  ls /var/log/nginx/*.log |xargs truncate -s 0
    ```

7. 修改项目config: `/common/config.py`


8.  **todo** 配置spider :
    - empty mysql
    - database.json

9. 启动工具链:
    - `cd spider && bash -x restart_spider.sh`

