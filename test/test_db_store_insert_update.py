import sys
import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
from database import dispatch


def run():
    conn = dispatch.MultiDB()

    test_data = {'public_ip': 'fake_ip', 'node_id': '123', 'neighbours': 10, 'last_update_time': 10}
    test_data2 = {'public_ip': 'fake_ip', 'node_id': '123', 'neighbours': 10, 'last_update_time': 20}
    update_list = ['neighbours','last_update_time']

    conn.insert_update_into_db("test_db", "kadinfo_root", test_data,update_list)
    conn.insert_update_into_db("test_db", "kadinfo_root", test_data2,update_list)

if __name__ == '__main__':
    run()
