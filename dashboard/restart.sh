ps -ef |grep dash.py | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9

nohup python3 dash.py &