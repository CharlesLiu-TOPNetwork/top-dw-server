### TOP-DW-server
record update log .

### Usage
0. vvlinux:
``` 
pip3 install virtualenv
source  vvlinux/bin/activate
pip3 install -r requirements.txt
```
1. nginx
    - to be completed

2. redis
    - to be completed

3. proxy
    -(vvlinux) `nohup python3 proxy.py &`

4. consumer
    -(vvlinux) `nohup python3 main_consumer.py -t test`


#### 0624
1. support regular metrics && multi mysql database
