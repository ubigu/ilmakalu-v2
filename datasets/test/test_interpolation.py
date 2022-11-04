import unittest


from modules.interpolate import Point, Interpolation


class TestInterpolation(unittest.TestCase):
    def test_k_computation_0(self):
        p0 = Point(0, 0)
        p1 = Point(1, .5)

        intp = Interpolation(p0, p1)
        result = intp.interpolate(2)
        self.assertEqual(result, 1)

    def test_k_computation_1(self):
        p0 = Point(1, .5)
        p1 = Point(0, 0)

        intp = Interpolation(p0, p1)
        result = intp.interpolate(2)
        self.assertEqual(result, 1)
        
    def test_interpolation_when_k_and_b_given_case_0(self):
        intp = Interpolation(k=2, b=0)
        result = intp.interpolate(1)
        self.assertEqual(result, 2)

        self.assertEqual(intp.interpolate(-100), -200)

    def test_interpolation_when_k_and_b_given_case_1(self):
        intp = Interpolation(k=2, b=.5)
        result = intp.interpolate(1)
        self.assertEqual(result, 2.5)

        self.assertEqual(intp.interpolate(-100), -199.5)

    def test_wrong_initialization_0(self):
        self.assertRaises(ValueError,Interpolation, k=1)

    def test_wrong_initialization_1(self):
        self.assertRaises(ValueError,Interpolation, b=1)

    def test_wrong_initialization_2(self):
        self.assertRaises(ValueError,Interpolation, p_0=Point(0,0))

    def test_wrong_initialization_3(self):
        self.assertRaises(ValueError,Interpolation, p_1=Point(0,0))

    def test_wrong_initialization_4(self):
        self.assertRaises(ValueError,Interpolation, p_0=Point(0,0), k=1)

    def test_wrong_initialization_5(self):
        self.assertRaises(ValueError,Interpolation, p_1=Point(0,0), b=1)

    def test_wrong_initialization_6(self):
        self.assertRaises(ValueError,Interpolation, p_1=Point(0,0), k=1, b=1)

    def test_wrong_initialization_7(self):
        p = Point(0, 0)
        self.assertRaises(ValueError,Interpolation, p, p)
