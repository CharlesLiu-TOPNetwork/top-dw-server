import subprocess
import time

check_interval = 5 # every 5 seconds

consumer_process_count = 15
proxy_process_count = 2
dash_process_count = 2

project_path = '/home/charles/project/top-dw'
format_regex = '%Y-%m-%d %H:%M:%S'
def now_time():
    return time.strftime(format_regex, time.localtime(time.time()))

def check_true_or_restart(component_path:str,process_name:str,expected_num:int,start_cmd:str):
    res = subprocess.getoutput('ps -ef |grep {0} | grep -v grep | grep -v nohup -c'.format(process_name))
    print("{0} cnt {1}, expected {2}".format(process_name,res,expected_num))
    if int(res) !=expected_num:
        print("try restart {0}, time: {1}".format(process_name,now_time()))
        cmd_str = "ps -ef |grep " + process_name + " | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9"
        print(cmd_str)
        res = subprocess.getoutput(cmd_str)
        print(res)
        res = subprocess.call("cd {0} && source vvlinux/bin/activate && cd {1} && {2}".format(project_path,component_path,start_cmd),shell=True)
        time.sleep(1)
        print(res)

if __name__ == '__main__':
    while True:
        check_true_or_restart('consumer/','main_consumer.py',consumer_process_count,'nohup python3 main_consumer.py -t test & \n')
        check_true_or_restart('proxy/','proxy.py',proxy_process_count,'nohup python3 proxy.py & \n')
        check_true_or_restart('dashboard/','dash.py',dash_process_count,'nohup python3 dash.py & \n')
        time.sleep(60)
        
