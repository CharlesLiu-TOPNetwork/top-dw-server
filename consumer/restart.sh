ps -ef |grep main_consumer | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9

nohup python3 main_consumer.py -t test & 