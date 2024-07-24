import unittest

from utils import DataPoint, add_data_point, get_data_points, filter_points

data1_1 = [1, 2, 1, 3, 1, 6, 5, 4, 1, 10, 3, 4, 2, 0, 8, 7, 8, 3, 5]
data1_2 = [1, 1, 2, 3, 4, 5, 5, 1, 3, 2, 4, 2, 2, -15, 2, 2, 3, 4, 5, 1, 2, 3, 4, 5]
data1_3 = [1, 1, 1, 3, 1, 3, 5, 6, 2, -1, 36, 5, 4, 6, 5, 6, 4, 6, 3, 3, 5, 4, 6, 4, 5]

data2_1 = [12, 17, 12, 12, 21, 13, 15, 15, 17, 50, 20, 22, 21, 20, 123, 23, 25]
data2_2 = [12, 20, 21, 12, 15, 17, 0, 20, 12, 32, 12, 23, 25]
data2_3 = [12, 21, 21, 12, 15, 17, -2, 20, 14, 15, 12, 12, 23, 25]

data3_1 = [0, 0, 1, 100, 1, 2, 3, 4, 5]
data3_2 = [0, 0, 0, 100, 0, 0, 0, 0]
data3_3 = [1000, 2000, 3000, 20000, 4000, 5000, 6000]

data_with_outliers = [data1_1, data1_2, data1_3, data2_1, data2_2, data2_3, data3_1, data3_2, data3_3]
outliers = [10, 15, 36, 50, 0, -2, 100, 100, 20000]

data_without_outliers = [[1, 2, 3, 4, 5, 6, 7, 8, 9], [100, 200, 300, 400, 500, 600, 800],
                         [10, 4, 3, -1, -5, -10, -12, 14], [1000, 1000, 1000, 1000, 1001, 1000, 1000, 1000, 1000, 1000]]


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
    def test_outfiltering(self):
        for x, outlier in zip(data_with_outliers, outliers):
            points = [DataPoint(0,a) for a in x]
            b = filter_points(points)
            self.assertNotIn(DataPoint(0,outlier), b)

    def test_leaving(self):
        for x in data_without_outliers:
            points = [DataPoint(0,a) for a in x]
            b = filter_points(points)
            self.assertEqual(points, b)



if __name__ == "__main__":
    unittest.main()
