
"""
simple unit tests for this package
"""

import os
import sys
import unittest

_test_path = os.path.dirname(__file__)
_path = os.path.join(_test_path, '..', 'src')
if _path not in sys.path:
    sys.path.insert(0, _path)

import adl2pydm


class Test_Something(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_the_package_name(self):
        self.assertEqual(adl2pydm.__project__, u'adl2pydm')


def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        Test_Something,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
