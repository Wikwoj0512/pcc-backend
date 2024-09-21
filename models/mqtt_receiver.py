import json
import threading
import time
from copy import deepcopy

import requests
from flask import logging
from flask_socketio import SocketIO

import paho.mqtt.client as mqtt

from .profiles_handler import ProfilesHandler
from .session import Session
from utils import js_long_to_date, DataPoint, parse_dict, check_location_difference


class MqttReceiver:
    def __init__(self, config='app_config.json', host='localhost', port=1883, topic='pcc/in',
                 status_application='http://localhost:2138/', profiles_config='profiles-config.json'):
        self.running = True
        self.status_application = status_application

        with open(config, encoding='utf-8') as f:
            self.config = json.loads(f.read())
        self.client = mqtt.Client()

        self.topics = []
        self.client.on_message = self.recieve_message

        def on_client_connect(client, *args, **kwargs):
            print(f'Connecting to topic {topic}')
            client.subscribe(topic)

        self.client.on_connect = on_client_connect
        self.client.connect(host, port)

        self.socketio = None

        self.data = {}
        self.locations = {}
        self.location_history = {}
        self.origins_changed = False

        self.location_origins_changed = False
        self.last_trail_points = {}
        self.changed_trail_points = []

        self.sessions = {}
        self.raw_values = {}
        self.profiles_config = profiles_config
        self.profiles_handler = None

        self.run_forever()

    def connect_client(self):
        self.client.subscribe(self.topic)

    def infinite_sender(self, socketio: SocketIO):

        self.socketio = socketio
        if self.profiles_config:
            try:
                self.profiles_handler = ProfilesHandler(self.profiles_config, socketio)
            except Exception as e:
                print(f'failed to create profiles handler: {e}')

        while self.running:

            if self.profiles_handler is not None:
                self.profiles_handler.emit()
            for session in self.sessions.values():
                session.execute(self.data, socketio)

            self.emit_raw_values(socketio)

            for session in self.sessions.values():
                session.send_locations(self.locations, socketio)
            if len(self.changed_trail_points):
                for session in self.sessions.values():
                    session.send_trail_locations(self.last_trail_points, self.changed_trail_points, socketio)
                self.changed_trail_points = []
            time.sleep(0.5)

            if self.origins_changed:
                self.origins_changed = False
                socketio.emit('charts/origins', self.get_origins())
            if self.location_origins_changed:
                self.location_origins_changed = False
                socketio.emit('maps/origins', self.get_location_origins())
        print("Quitting receiver")
        self.client.loop_stop()

    def status_sender(self):
        while self.running:
            try:
                response = requests.get(self.status_application)
                if response.status_code == 200:
                    self.socketio.emit('statuses/data', response.json())
                    time.sleep(0.2)
                    continue
                raise ValueError('Received invalid status code')
            except Exception as e:
                print(e)
                time.sleep(5)

    def run_forever(self):
        ft = threading.Thread(target=self.client.loop_forever)
        ft.start()
        st = threading.Thread(target=self.status_sender)
        st.start()

    def recieve_message(self, _client, _userdata, msg: mqtt.MQTTMessage):
        try:
            message = json.loads(msg.payload)
        except Exception as e:
            print(f"Failed to decode message, exception: {e}, message: {msg.payload}")
            return
        try:
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

            current_origin_value = self.raw_values.get(origin, {"name": origin, 'keys': {}})

            current_origin_value['timestamp'] = timestamp
            current_origin_value['displayName'] = self.get_origin_display_name(origin)

            message_keys = []
            for key, value in parsed.items():
                if value is None:
                    continue

                self.check_origin(origin, key)

                self.data[origin][key].append(DataPoint(timestamp, value))
                current_origin_value['keys'][key] = {'value': value}

                message_keys.append(key)
                if self.profiles_handler is not None:
                    self.profiles_handler.add_value(origin, key, value)

            key_names = self.get_origin_keys_display_names(origin, message_keys)

            for key in key_names:
                key_name = key['name']
                current_origin_value['keys'][key_name] = {**key, **current_origin_value['keys'][key_name]}
            self.raw_values[origin] = current_origin_value
            if self.profiles_handler is not None:
                self.profiles_handler.emit_new()
        except Exception as e:
            print(f"unsupported message: {e}")

    def send_last_messages(self):
        if self.socketio:
            self.socketio.emit('raw/data', self.data)

    def get_origin_display_name(self, origin: str):
        origin_config = self.config.get('origins', {}).get(origin, {})
        return origin_config.get('displayName', origin)

    def get_origin_keys_display_names(self, origin: str, keys: list[str]):
        origin_config = self.config.get('origins', {}).get(origin, {})
        display_names = origin_config.get('keys', {})
        return [{"name": key, "displayName": display_names.get(key, key)} for key in keys]

    def parse_locations(self, origin: str, keys):
        origin_location = self.locations.get(origin, {})
        new_location = deepcopy(origin_location)
        for key, val in keys:
            if 'location' in key:
                if key.endswith('longitude'):
                    new_location['lng'] = val
                    continue
                if key.endswith('latitude'):
                    new_location['lat'] = val
                    continue
                if key.endswith('height'):
                    new_location['alt'] = val
                    continue
        if not len(origin_location.items()):
            self.location_origins_changed = True

        if new_location.get('lat') is not None and new_location.get('lng') is not None:
            self.locations[origin] = new_location
            last_trail = self.last_trail_points.get(origin, {})
            if check_location_difference(last_trail, new_location, 5):
                self.last_trail_points[origin] = new_location
                self.add_location_to_history(origin, new_location)
                self.changed_trail_points.append(origin)

    def add_location_to_history(self, origin, location):
        previous_locations = deepcopy(self.location_history.get(origin, []))

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
        for origin, value in deepcopy(self.locations).items():
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

    def get_location_origins(self):
        origins_list = []
        for origin in list(self.location_history.keys()):
            origins_list.append({'name': origin, 'displayName': self.get_origin_display_name(origin)})
        return origins_list

    def emit_raw_values(self, socketio):
        emit_value = {}
        for key, value in self.raw_values.items():
            new_value = {**value, 'keys': list(value.get('keys').values())}
            emit_value[key] = new_value
        socketio.emit('raw/data', emit_value)

    def check_origin(self, origin, key):
        previous_data_point = self.data[origin].get(key)
        if previous_data_point is None:
            self.data[origin][key] = []
            self.origins_changed = True
