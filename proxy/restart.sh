ps -ef |grep "proxy:app" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9

nohup gunicorn -w 4 -b 127.0.0.1:9092 proxy:app & 