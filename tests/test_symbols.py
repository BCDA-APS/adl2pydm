
"""
unit tests for module: symbols
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest

# turn off logging output
logging.basicConfig(level=logging.CRITICAL)

_test_path = os.path.dirname(__file__)
_path = os.path.join(_test_path, '..', 'src')
if _path not in sys.path:
    sys.path.insert(0, _path)

from adl2pydm import symbols


class Test_Module(unittest.TestCase):

    # def setUp(self): ...

    # def tearDown(self): ...

    def test_symbols(self):
        self.assertEqual(len(symbols.adl_widgets), 24)

        self.assertIsInstance(symbols.adl_widgets, dict)
        for k, w in symbols.adl_widgets.items():
            self.assertIsInstance(w, dict)
            self.assertEqual(len(w), 2)
        # "arc" : dict(type="static", pydm_widget="PyDMDrawingArc"),
        w = symbols.adl_widgets["arc"]
        self.assertEqual(w["type"], "static")
        self.assertEqual(w["pydm_widget"], "PyDMDrawingPie")
        self.assertEqual(w["type"], "static")

        self.assertEqual(len(symbols.pydm_widgets), 33)
        self.assertIsInstance(symbols.pydm_widgets, dict)
        for k, w in symbols.pydm_widgets.items():
            self.assertIsInstance(w, symbols.PyDM_CustomWidget)
            self.assertEqual(len(w), 3)
        #     PyDMLabel = PyDM_CustomWidget("PyDMLabel", "QLabel", "pydm.widgets.label"),
        w = symbols.pydm_widgets["PyDMLabel"]
        self.assertEqual(w.cls, "PyDMLabel")
        self.assertEqual(w.extends, "QLabel")
        self.assertEqual(w.header, "pydm.widgets.label")



def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        Test_Module,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
