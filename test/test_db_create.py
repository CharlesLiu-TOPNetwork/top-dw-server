import sys
import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
from database import dispatch


def run():
    conn = dispatch.MultiDB()
    test_data = {
        'uniq_hash': 123, 'msg_hash': 123, 'msg_size': 123, 'send_timestamp': 123,'packet_size':1234
    }
    conn.insert_into_db("test_db", "p2p", test_data)
    conn.insert_into_db("test_db2", "p2p", test_data)

if __name__ == '__main__':
    run()
