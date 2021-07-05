ps -ef |grep proxy |grep top-dw | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9

nohup python3 proxy.py & 