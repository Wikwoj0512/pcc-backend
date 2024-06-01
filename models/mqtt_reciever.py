import json
import threading
import time

import paho.mqtt.client as mqtt

from .session import Session
from utils import js_long_to_date, DataPoint, parse_dict


class MqttReciever:
    def __init__(self, host='localhost', port=1883, topic='pcc_in'):

        self.client = mqtt.Client()

        self.topics = []
        self.client.on_message = self.recieve_message

        self.client.connect(host, port, 60)
        self.client.subscribe(topic)

        self.last_message = None
        self.data = {}

        self.sessions = {}
        self.run_forever()

    def infinite_sender(self, socketio):
        while True:
            for session in self.sessions.values():
                session.execute(self.data, socketio)
            time.sleep(0.5)

    def run_forever(self):
        t = threading.Thread(target=self.client.loop_forever)
        t.start()

    def recieve_message(self, client, userdata, msg):
        message = json.loads(msg.payload)
        header = message.get('header')
        if not header:
            return
        origin = header.get('origin')

        data = message.get('data')
        if data is None or origin is None: return

        timestamp = header.get('timestamp')
        if not timestamp: return
        high = timestamp.get('high')
        low = timestamp.get('low')
        signed = timestamp.get('unsigned')
        if (high is None or low is None or signed is None): return

        timestamp = js_long_to_date(high, low, signed)
        previous = self.data.get(origin)

        if previous is None:
            self.data[origin] = {}
        parsed = parse_dict(data)
        for key, value in parsed.items():

            previous_data_point = self.data[origin].get(key)
            if previous_data_point is None:
                self.data[origin][key] = []

            self.data[origin][key].append(DataPoint(timestamp, value))

    def get_origns(self):
        return [{"origin": origin, 'keys': list(v.keys())} for (origin, v) in self.data.items()]

    def get_keys(self, origin):
        origin = self.data.get(origin)
        if origin is None:
            return {'error': f'no data for origin {origin}'}

        return list(origin.keys())

    def create_session(self, session_name):
        self.sessions[session_name] = Session(session_name)
        return session_name

    def get_session(self, session_name):
        return self.sessions.get(session_name)

    def remove_session(self, session_name):
        session = self.get_session(session_name)
        if not session:
            return False
        session.kill()
        self.sessions.pop(session_name)
