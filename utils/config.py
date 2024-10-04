import argparse

import yaml


class Config:
    def __init__(self):
        parser = argparse.ArgumentParser(
            prog='Pcc backend',
            description='Running without args will load default config, use --config to specify config file or --console to specify command line arguments')

        parser.add_argument('--config', help="Config file name", default="config.yaml", type=str)
        parser.add_argument('--pcc-port', help="port for pcc", type=int)
        parser.add_argument('--mqtt-topic', help='pcc in topic name', type=str)
        parser.add_argument('--mqtt-host', help='mqtt host', type=str)
        parser.add_argument('--mqtt-port', help='mqtt port', type=int)
        parser.add_argument('--receiver-config', help="receiver config file", type=str)
        cmd_line_args = vars(parser.parse_args())
        cfg_file_args = self.read_args_from_cfg_file(cmd_line_args.get("config"))
        for k, v in cmd_line_args.items():
            if v is not None:
                cfg_file_args[k] = v

        # assign
        print(cfg_file_args)
        self.pcc_port = cfg_file_args.get('pcc_port', 2137)
        self.mqtt_topic = cfg_file_args.get('mqtt_topic', 'pcc/in')
        self.mqtt_host = cfg_file_args.get('mqtt_host', 'localhost')
        self.mqtt_port = cfg_file_args.get('mqtt_port', 1883)
        self.receiver_config = cfg_file_args.get('receiver_config', 'app_config.json')

    def assign_args_from_cmd_line(self, args):
        print(vars(args))
        for arg in vars(args):
            self[arg] = args[arg]

    def read_args_from_cfg_file(self, config_file):
        contents = {}
        try:
            with open(config_file) as f:
                contents = yaml.safe_load(f)
        except Exception as e:
            print(e)
        return contents

    def __repr__(self):
        return f"Hosting PCC on port {self.pcc_port}, receiving mqtt traffic from {self.mqtt_host}:{self.mqtt_port} on topic {self.mqtt_topic} and parsing it according to {self.receiver_config} and fetching from status app on {self.status_app}"