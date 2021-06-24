import sys
import os
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(project_path))
from consumer import metrics_timer_consumer
from consumer import metrics_counter_consumer
from consumer import metrics_flow_consumer


def timer():
    packet = {'alarm_type': 'metrics_timer', 'packet': {'env': 'test2', 'send_timestamp': 1624512831, 'public_ip': '192.168.181.128', 'category': 'xcons', 'tag': 'network_message_dispatch', 'count': 3060, 'max_time': 93926, 'min_time': 18, 'avg_time': 153}}
    timer_consumer = metrics_timer_consumer.MetricsTimerConsumer("","")
    timer_consumer.metrics_timer_handle(packet.get('packet'))

def counter():
    packet = {'alarm_type': 'metrics_counter', 'packet': {'env': 'test2', 'public_ip': '192.168.181.128', 'send_timestamp': 1624513771, 'category': 'db', 'tag': 'key_block_output_resource', 'count': 2278, 'value': 597136}}
    counter_consumer = metrics_counter_consumer.MetricsCounterConsumer("","")
    counter_consumer.metrics_counter_handle(packet.get('packet'))

def flow():
    packet = {'alarm_type': 'metrics_flow', 'packet': {'env': 'test2', 'public_ip': '192.168.181.128', 'send_timestamp': 1624513771, 'category': 'vhost', 'tag': 'handle_data_ready_called', 'count': 3340, 'max_flow': 10, 'min_flow': 1, 'sum_flow': 4146, 'avg_flow': 1, 'tps_flow': 1683, 'tps': '9.34'}}
    flos_consumer = metrics_flow_consumer.MetricsFlowConsumer("","")
    flos_consumer.metrics_flow_handle(packet.get('packet'))


if __name__ == '__main__':
    timer()
    counter()
    flow()
