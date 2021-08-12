ps -ef |grep "spider.py" | grep -v grep | awk -F ' ' '{print $2}' | xargs kill -9
echo "" > nohup.out
source ../vvlinux/bin/activate
nohup python3 -u spider.py >> nohup.out 2>&1 & 
date