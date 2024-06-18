import argparse

import yaml


class Config:
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog='Pcc backend',
            description='Running without args will load default config, use --config to specify config file or --console to specify command line arguments')

        parser.add_argument('--config', help="Config file name")
        parser.add_argument('--console', action='store_true')
        parser.add_argument('--pcc-port', help="port for pcc")
        parser.add_argument('--mqtt-topic', help='pcc in topic name')
        parser.add_argument('--mqtt-host', help='mqtt host')
        parser.add_argument('--mqtt-port', help='mqtt port')
        parser.add_argument('--reciever-config', help="reciever config file")
        args = parser.parse_args()

        if args.console:
            self.analyze_console(args)
            return

        self.analyze_config_file(args.config if args.config else 'app_config.yaml')

    def analyze_console(self, args):
        self.pcc_port = int(args.pcc_port) if args.pcc_port else 2137
        self.mqtt_topic = args.mqtt_topic if args.mqtt_topic else 'pcc/in'
        self.mqtt_host = args.mqtt_host if args.mqtt_host else 'localhost'
        self.mqtt_port = int(args.mqtt_port) if args.mqtt_port else 1883
        self.reciever_config = args.reciever_config if args.reciever_config else 'app_config.json'

    def analyze_config_file(self, config_file):
        try:
            with open(config_file) as f:
                contents = yaml.safe_load(f)
            print(contents, type(contents))
            self.pcc_port = int(contents.get('pcc-port', 2137))
            self.mqtt_topic = contents.get('mqtt-topic', 'pcc/in')
            self.mqtt_host = contents.get('mqtt-host', 'localhost')
            self.mqtt_port = int(contents.get('mqtt-port', 1883))
            self.reciever_config = contents.get('reciever-config', 'app_config.json')
        except Exception as e:
            print(e)
            self.pcc_port = 2137
            self.mqtt_topic = 'pcc/in'
            self.mqtt_host = 'localhost'
            self.mqtt_port = 1883
            self.reciever_config = 'app_config.json'

    def __repr__(self):
        return f"Hosting PCC on port {self.pcc_port}, recieving mqtt traffic from {self.mqtt_host}:{self.mqtt_port} on topic {self.mqtt_topic} and parsing it according to {self.reciever_config}"
