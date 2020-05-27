
"""
simple unit tests for this package
"""

import logging
import json
import os
import sys
import unittest

# turn off logging output
logging.basicConfig(level=logging.CRITICAL)

_test_path = os.path.dirname(__file__)
_path = os.path.join(_test_path, '..', 'src')
if _path not in sys.path:
    sys.path.insert(0, _path)

from adl2pydm import calc2rules


class TestSuite(unittest.TestCase):

    def setUp(self):
        path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "test_calcs.json",
            )
        )

        with open(path, "r") as f:
            buf = f.read()

        self.test_calcs = json.loads(buf)

    # ----------------------------------------------------------

    def test_example_calcs(self):
        for testcase in self.test_calcs:
            rule = calc2rules.convertCalcToRuleExpression(testcase[0])
            equal = rule == testcase[-1]
            self.assertEqual(rule, testcase[-1], testcase[0])


def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        TestSuite,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
