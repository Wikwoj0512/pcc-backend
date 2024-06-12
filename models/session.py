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

    def get_points(self, data):
        ret_data = {}
        for field in self.fields:
            origin = field.get('origin')
            keys = field.get('keys')
            ret_data[origin] = {}
            for key in keys:
                points = data.get(origin).get(key)
                if not len(points):
                    ret_data[origin][key] = []
                    continue
                timestamp = points[-1].timestamp - self.timeframe
                points = get_data_points(points, timestamp)
                points = largest_triangle_three_buckets(points, self.points)
                points = [[point.timestamp, point.value] for point in points]
                ret_data[origin][key] = points
        return ret_data
