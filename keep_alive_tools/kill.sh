ps -ef |grep "keep_alive.py" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9