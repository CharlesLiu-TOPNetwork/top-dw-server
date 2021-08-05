echo "" > nohup.out
source ../vvlinux/bin/activate
nohup python3 -u spider.py >> nohup.out 2>&1 & 
date