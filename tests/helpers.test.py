import unittest

from utils import DataPoint, add_data_point, get_data_points


class TestHelpers(unittest.TestCase):
    def test_add_data_point(self):
        data = [DataPoint(1, 1), DataPoint(2, 2), DataPoint(3, 3), DataPoint(4, 4)]
        expected = [DataPoint(1, 1), DataPoint(2, 2), DataPoint(2.5, 2.5), DataPoint(3, 3), DataPoint(4, 4)]
        result = add_data_point(data, 2.5, 2.5)
        self.assertEqual([[p.value, p.timestamp] for p in result], [[p.value, p.timestamp] for p in expected])

    def test_get_data_points(self):
        data = [DataPoint(1, 1), DataPoint(2, 2), DataPoint(3, 3), DataPoint(4, 4)]
        result = get_data_points(data, 2.5)
        self.assertEqual([[p.value, p.timestamp] for p in result],
                         [[p.value, p.timestamp] for p in [DataPoint(3, 3), DataPoint(4, 4)]])


if __name__ == "__main__":
    unittest.main()
