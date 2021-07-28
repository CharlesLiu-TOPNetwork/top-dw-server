### TOP-DW-server
record update log .

### Usage
0. vvlinux:
    ``` 
    pip3 install virtualenv
    virtualenv  -p /usr/bin/python3 vvlinuxs

    source  vvlinux/bin/activate
    pip3 install -r requirements.txt
    ```
1. nginx
    ```
    yum -y install gcc gcc-c++ make libtool zlib zlib-devel openssl openssl-devel pcre pcre-devel

    mkdir /root/temp -p && cd /root/temp
    wget http://nginx.org/download/nginx-1.14.2.tar.gz
    tar zxvf nginx-1.14.2.tar.gz
    cd nginx-1.14.2
    ./configure --with-http_stub_status_module --with-http_ssl_module --with-pcre
    make -j4 && make install

    ```

2. redis
    ```
    yum install redis -y
    vi /etc/redis.conf
    # 端口 bind 0.0.0.0;
    # 480行可以修改redis密码 requirepass yourpasswd;
    redis-server [config_path] &
    redis-cli -a yourpasswd 验证启动成功
    ```

3. 启动工具链:
    - `cd keep_alive_tools/ && bash -x start.sh`

4. 关掉工具链：
    - `cd keep_alive_tools/ && bash -x kill.sh`



#### 0624
1. support regular metrics && multi mysql database
