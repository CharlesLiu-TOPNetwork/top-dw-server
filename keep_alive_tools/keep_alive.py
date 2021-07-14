import subprocess
import time

check_interval = 60 # every 1 min
restart_dashboard_interval = 180 # every three hours
global_restart_dashboard_interval = 0 # counter

consumer_process_count = 17
proxy_process_count = 2
dash_process_count = 2

project_path = '/home/charles/project/top-dw-server'
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

def restart_dash(component_path:str,process_name:str,start_cmd:str):
    global global_restart_dashboard_interval
    if global_restart_dashboard_interval == restart_dashboard_interval:
        # print(global_restart_dashboard_interval)
        global_restart_dashboard_interval = 0
        
        res = subprocess.call('cd {0} && date | xargs echo > keep_alive_tools/nohup.out'.format(project_path),shell=True)
        print(res)
        print("try kill && restart dashboard  && clear log.")
        
        cmd_str = "ps -ef |grep " + process_name + " | grep -v grep | awk -F ' ' '{print $2}'| xargs kill -9"
        print(cmd_str)
        res = subprocess.getoutput(cmd_str)
        print(res)
        res = subprocess.call("cd {0} && source vvlinux/bin/activate && cd {1} && {2}".format(project_path,component_path,start_cmd),shell=True)
        time.sleep(1)

    else:
        global_restart_dashboard_interval +=1
        # print(global_restart_dashboard_interval)

    return

if __name__ == '__main__':
    while True:
        check_true_or_restart('consumer/','main_consumer.py',consumer_process_count,'nohup python3 main_consumer.py -t test & \n')
        check_true_or_restart('proxy/','proxy.py',proxy_process_count,'nohup python3 proxy.py & \n')
        check_true_or_restart('dashboard/','dash.py',dash_process_count,'nohup python3 dash.py & \n')
        restart_dash('dashboard/','dash.py','nohup python3 dash.py & \n')
        time.sleep(check_interval)
        
