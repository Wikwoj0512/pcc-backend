from utils import get_data_points, largest_triangle_three_buckets


class Session:
    def __init__(self, session_id):
        self.session_id = session_id
        self.fields = []
        self.timeframe = 0.1
        self.points = 10

    def execute(self, data, socketio):
        points = self.get_points(data)
        socketio.emit('data', points, namespace='/', to=self.session_id)

    def configure(self, data):
        self.fields = []
        for el in data.get("keys", []):
            if not el:
                continue
            origin = el.get('origin')
            keys = el.get('keys')
            if origin is None or keys is None or not isinstance(origin, int) or not isinstance(keys, list):
                return "Wrong request structure {origin: string, keys: string[]}[]"
            for key in keys:
                if not isinstance(key, str):
                    return "Wrong request structure {origin: string, keys: string[]}[]"
            self.fields.append({'origin': origin, 'keys': keys})
        try:
            self.timeframe = int(data.get("timestamp", self.timeframe))
        except Exception as e:
            print(f"Failed to set timeframe for data {data}: {e}")
        try:
            self.points = int(data.get("points", self.points))
        except Exception as e:
            print(f"Failed to set points for data {data}: {e}")
        return None

    def get_points(self, data):
        ret_data = []
        for field in self.fields:
            origin = field.get('origin')
            keys = field.get('keys')
            for key in keys:
                points = data.get(origin).get(key)
                if not len(points):
                    ret_data.append({'values': [], 'origin': origin, 'key': key})
                timestamp = points[-1].timestamp - self.timeframe

                points = get_data_points(points, timestamp)
                points = largest_triangle_three_buckets(points, self.points)
                points = [[point.timestamp, point.value] for point in points]
                ret_data.append({'values': points, 'origin': origin, 'key': key})
        return ret_data
