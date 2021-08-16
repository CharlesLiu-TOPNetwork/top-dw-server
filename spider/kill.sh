ps -ef |grep "spider.py" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9
ps -ef |grep "main_consumer.py" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9
ps -ef |grep "proxy:app" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9
ps -ef |grep "dash.py" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9