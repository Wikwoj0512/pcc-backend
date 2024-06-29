import hashlib
import random
from copy import deepcopy
from math import sqrt
from typing import Dict, List

import numpy as np
from geopy.distance import distance


class DataPoint:
    def __init__(self, timestamp, value):
        self.timestamp = timestamp
        self.value = value

    def __gt__(self, other):
        return self.timestamp > other.timestamp

    def __repr__(self):
        return f"{self.timestamp}: {self.value}"


DataType = Dict[str, Dict[str, List[DataPoint]]]


def create_session_name(n: int) -> str:
    return hashlib.md5(str(n).encode('utf-8')).hexdigest()[::2] + hashlib.md5(
        str(random.randint(69, 2137)).encode('utf-8')).hexdigest()[::-2]


def js_long_to_date(high, low, unsigned):
    """
    Convert a JavaScript long (with high and low parts) to a Python datetime object.

    :param high: int, the high part of the 64-bit integer
    :param low: int, the low part of the 64-bit integer
    :param unsigned: bool, whether the number is unsigned
    :return: timestamp
    """
    if unsigned:
        # Combine high and low parts for an unsigned 64-bit integer
        full_int = (high << 32) | low
    else:
        # Combine high and low parts for a signed 64-bit integer
        if high & 0x80000000:  # If the sign bit is set in the high part
            full_int = ((high << 32) | low) - (1 << 64)
        else:
            full_int = (high << 32) | low

    # Convert milliseconds to seconds
    return full_int / 10000


def add_data_point(data: list[DataPoint], value: float, timestamp: float):
    point = DataPoint(timestamp, value)
    ret_data = deepcopy(data)
    if len(data) == 0:
        return [point]
    if point > data[-1]:
        ret_data.append(point)
        return ret_data
    start = 0
    end = len(data) - 1
    mid = (start + end) // 2
    while start < end:
        if data[mid] > point:
            end = mid
        else:
            start = mid + 1
        mid = (start + end) // 2

    ret_data.insert(start, point)
    return ret_data


def get_data_points(data: list[DataPoint], timestamp: float) -> list[DataPoint]:
    start = 0
    end = len(data) - 1
    mid = (start + end) // 2
    while start < end:
        if data[mid].timestamp > timestamp:
            end = mid
        else:
            start = mid + 1
        mid = (start + end) // 2
    return data[start:]


def largest_triangle_three_buckets(data, target_count):
    if target_count >= len(data) or target_count <= 0:
        return data

    bucket_size = (len(data) - 2) / (target_count - 2)
    reduced_data = [data[0]]  # Always include the first point

    for i in range(1, target_count - 1):
        # Calculate the range for the current bucket
        range_start = int(np.floor((i - 1) * bucket_size)) + 1
        range_end = int(np.floor(i * bucket_size)) + 1

        # Get the average X and Y values for the next bucket
        next_range_start = int(np.floor(i * bucket_size)) + 1
        next_range_end = int(np.floor((i + 1) * bucket_size)) + 1
        next_bucket = data[next_range_start:next_range_end]
        avg_x = np.mean([p.timestamp for p in next_bucket])
        avg_y = np.mean([p.value for p in next_bucket])

        # Find the point with the largest triangle area
        range_data = data[range_start:range_end]
        a = data[range_start - 1]
        max_area = -1
        chosen_point = None

        for point in range_data:
            area = abs((a.timestamp - avg_x) * (point.value - a.value) - (a.timestamp - point.timestamp) * (
                    avg_y - a.value)) / 2
            if area > max_area:
                max_area = area
                chosen_point = point

        reduced_data.append(chosen_point)

    reduced_data.append(data[-1])  # Always include the last point
    return reduced_data


def parse_dict(data: dict):
    ret_dict = {}
    for key, val in data.items():
        if isinstance(val, dict):
            high_dict = parse_dict(val)
            for k, v in high_dict.items():
                ret_dict[f"{key}.{k}"] = v
        else:
            ret_dict[key] = val

    return ret_dict


def check_location_difference(location1, location2):
    coords_1 = (location1.get('lng'), location1.get('lat'))
    coords_2 = (location2.get('lng'), location2.get('lat'))
    if None in coords_1 and not None in coords_2:
        return True
    if None in coords_1 or None in coords_2:
        return False
    dist = distance(coords_2, coords_1).m
    now_height = location1.get('alt', 0)
    last_height = location2.get('alt', 0)
    height_diff = abs(now_height - last_height)
    dist = sqrt(dist ** 2 + height_diff ** 2)
    return dist > 1
