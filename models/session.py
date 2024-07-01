from typing import Dict, List, Union

from flask_socketio import SocketIO

from utils import get_data_points, largest_triangle_three_buckets, DataType


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.fields = []
        self.timeframe = 0.1
        self.points = 10
        self.locations = []

    def execute(self, data: DataType, socketio: SocketIO):
        points = self.get_points(data)
        socketio.emit('charts/data', points, to=self.session_id)

    def configure(self, data: Dict[str, Union[Dict[str, List[str]], Union[str, float], Union[str, int]]]):
        # setting origins

        origins = data.get('origins')
        if origins is not None and isinstance(origins, dict):
            fields = []
            for origin, keys in origins.items():
                if not isinstance(keys, list):
                    continue
                if not isinstance(origin, str):
                    continue
                fields.append({'origin': origin, 'keys': keys})
            self.fields = fields

        # setting timeframe
        try:
            self.timeframe = float(data.get("timeframe", self.timeframe))
        except Exception as e:
            print(f"Failed to set timeframe for data {data}: {e}")
        # setting points
        try:
            self.points = int(data.get("points", self.points))
        except Exception as e:
            print(f"Failed to set points for data {data}: {e}")
        return None

    def get_points(self, data: DataType):
        ret_data = {}
        for field in self.fields:
            origin = field.get('origin')
            keys = field.get('keys')
            ret_data[origin] = {}
            for key in keys:
                points = data.get(origin)
                if not points:
                    continue
                points = points.get(key)
                if not points:
                    ret_data[origin][key] = []
                    continue
                timestamp = points[-1].timestamp - self.timeframe
                points = get_data_points(points, timestamp)
                points = largest_triangle_three_buckets(points, self.points)
                points = [[point.timestamp, point.value] for point in points]
                ret_data[origin][key] = points
        return ret_data

    def configure_locations(self, fields, locations_history):
        if not isinstance(fields, list):
            raise Exception("Wrong format")
        if not all([isinstance(x, str) for x in fields]):
            raise Exception("Wrong format")

        self.locations = fields

        ret_dict = {}
        for key in self.locations:
            history = locations_history.get(key)
            if history is not None and isinstance(history, list):
                ret_dict[key] = history[-200:]

        return ret_dict

    def send_locations(self, locations, socketio: SocketIO):
        ret_dict = {}
        for origin in self.locations:
            location = locations.get(origin)
            if location:
                ret_dict[origin] = location
        socketio.emit('maps/data', ret_dict, to=self.session_id)

    def send_trail_locations(self, last_trail_points, changed_trail_points, socketio):
        changed_locations = {}
        for x in changed_trail_points:
            if x in self.locations:
                trail_point = last_trail_points.get(x)
                if trail_point:
                    changed_locations[x] = trail_point
        socketio.emit('maps/trail', changed_locations, to=self.session_id)
