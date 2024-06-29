import json
import threading
import time
from copy import deepcopy
from typing import Any

from flask_socketio import SocketIO
from geopy.distance import distance
from math import sqrt

import paho.mqtt.client as mqtt

from .session import Session
from utils import js_long_to_date, DataPoint, parse_dict


class MqttReceiver:
    def __init__(self, config='app_config.json', host='localhost', port=1883, topic='pcc/in'):
        self.running = True

        with open(config, encoding='utf-8') as f:
            self.config = json.loads(f.read())
        self.client = mqtt.Client()

        self.topics = []
        self.client.on_message = self.recieve_message

        self.client.connect(host, port, 60)
        self.client.subscribe(topic)

        self.last_message = None
        self.data = {}
        self.locations = {}
        self.location_history = {}
        self.origins_changed = False

        self.sessions = {}
        self.run_forever()

    def infinite_sender(self, socketio: SocketIO):
        while self.running:
            for session in self.sessions.values():
                session.execute(self.data, socketio)
            time.sleep(0.5)
            if self.origins_changed:
                self.origins_changed = False
                socketio.emit('origins', self.get_origins(), namespace='/')
            socketio.emit('locations', self.get_locations())
        print("Quitting receiver")
        self.client.loop_stop()

    def run_forever(self):
        t = threading.Thread(target=self.client.loop_forever)
        t.start()

    def recieve_message(self, _client, _userdata, msg: mqtt.MQTTMessage):
        try:
            message = json.loads(msg.payload)
        except Exception as e:
            print(f"Failed to decode message, exception: {e}, message: {msg.payload}")
            return
        header = message.get('header')
        if not header:
            return
        origin = header.get('origin')

        data = message.get('data')
        if data is None or origin is None: return
        origin = str(origin)

        timestamp = header.get('timestamp')
        if not timestamp: return
        high = timestamp.get('high')
        low = timestamp.get('low')
        signed = timestamp.get('unsigned')
        if high is None or low is None or signed is None: return

        timestamp = js_long_to_date(high, low, signed)
        previous = self.data.get(origin)

        if previous is None:
            self.data[origin] = {}
            self.origins_changed = True
        parsed = parse_dict(data)
        self.parse_locations(origin, parsed.items())

        for key, value in parsed.items():
            previous_data_point = self.data[origin].get(key)
            if previous_data_point is None:
                self.data[origin][key] = []
                self.origins_changed = True

            self.data[origin][key].append(DataPoint(timestamp, value))

    def get_origin_display_name(self, origin: str):
        origin_config = self.config.get('origins', {}).get(origin, {})
        return origin_config.get('displayName', origin)

    def get_origin_keys_display_names(self, origin: str, keys: list[str]):
        origin_config = self.config.get('origins', {}).get(origin, {})
        display_names = origin_config.get('keys', {})
        return [{"name": key, "displayName": display_names.get(key, key)} for key in keys]

    def parse_locations(self, origin: str, keys):
        origin_location = self.locations.get(origin, {})
        for key, val in keys:
            if 'location' in key:
                if key.endswith('longitude'):
                    origin_location['lng'] = val
                    continue
                if key.endswith('latitude'):
                    origin_location['lat'] = val
                    continue
                if key.endswith('height'):
                    origin_location['alt'] = val
                    continue

        if origin_location.get('lat') is not None and origin_location.get('lng') is not None:
            self.locations[origin] = origin_location
            self.add_location_to_history(origin, origin_location)

    def add_location_to_history(self, origin, location):
        previous_locations = deepcopy(self.location_history.get(origin, []))
        if not len(previous_locations):
            self.location_history[origin] = [location, ]
            return
        last_position = previous_locations[-1]
        now_coords = (location.get('lng', 0), location.get('lat', 0))
        last_coords = (last_position.get('lng', 0), last_position.get('lat', 0))

        dist = distance(last_coords, now_coords).m
        now_height = location.get('alt', 0)
        last_height = last_position.get('alt', 0)
        height_diff = abs(now_height - last_height)
        dist = sqrt(dist ** 2 + height_diff ** 2)
        if dist > 1:
            previous_locations.append(location)
            self.location_history[origin] = previous_locations

    def get_origins(self):
        ret_list = []
        for (origin, v) in self.data.items():
            display_name = self.get_origin_display_name(origin)
            keys = self.get_origin_keys_display_names(origin, v.keys())
            ret_list.append(
                {"name": origin, "displayName": display_name, "keys": keys})
        return ret_list

    def get_locations(self):
        ret_data = {}
        for origin, value in self.locations.items():
            value["displayName"] = self.get_origin_display_name(origin)
            ret_data[origin] = value
        return ret_data

    def create_session(self, session_name: str):
        self.sessions[session_name] = Session(session_name)
        return session_name

    def get_session(self, session_name: str):
        return self.sessions.get(session_name)

    def remove_session(self, session_name: str):
        session = self.get_session(session_name)
        if not session:
            return False
        session.kill()
        self.sessions.pop(session_name)

    def get_location_history(self):
        return self.location_history

