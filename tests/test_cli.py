
"""
simple unit tests for this package
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

from adl2pydm import cli, output_handler


class Test_Main(unittest.TestCase):

    # these files both reader AND writer
    test_files = [
        "newDisplay.adl",                  # simple display
        "xxx-R5-8-4.adl",                  # related display
        "xxx-R6-0.adl",
        # "base-3.15.5-caServerApp-test.adl"  #  FIXME: needs more work here (unusual structure, possibly stress test):  # info[, "<<color rules>>", "<<color map>>"
        "calc-3-4-2-1-FuncGen_full.adl",   # strip chart
        "calc-R3-7-1-FuncGen_full.adl",    # strip chart
        "calc-R3-7-userCalcMeter.adl",     # meter
        "mca-R7-7-mca.adl",                # bar
        "motorx-R6-10-1.adl",
        "motorx_all-R6-10-1.adl",
        "optics-R2-13-1-CoarseFineMotorShow.adl",  # indicator
        "optics-R2-13-1-kohzuGraphic.adl", # image
        "optics-R2-13-1-pf4more.adl",      # byte
        "optics-R2-13-xiahsc.adl",         # valuator
        "scanDetPlot-R2-11-1.adl",         # cartesian plot, strip
        "sscan-R2-11-1-scanAux.adl",       # shell command
        "std-R3-5-ID_ctrl.adl",            # param
        # "beamHistory_full-R3-5.adl", # dl_color -- this .adl has content errors
        "ADBase-R3-3-1.adl",               # composite
        "simDetector-R3-3-31.adl",
        ]

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

        path = os.path.dirname(__file__)
        self.assertTrue(os.path.exists(path))

        self.medm_path = os.path.join(path, "medm")
        self.assertTrue(os.path.exists(self.medm_path))

    def tearDown(self):
        if os.path.exists(self.tempdir):
            shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_cli_main(self):
        # all example MEDM screens must process without errors
        for fname in os.listdir(self.medm_path):
            if not fname.lower().endswith(".adl"):
                continue
            full_name = os.path.join(self.medm_path, fname)
            self.assertTrue(os.path.exists(full_name))
            # print(full_name)

            sys.argv = [sys.argv[0], "-d", self.tempdir, full_name]
            # print(fname)
            cli.main()

            uiname = os.path.splitext(fname)[0] + output_handler.SCREEN_FILE_EXTENSION
            self.assertTrue(os.path.exists(os.path.join(self.tempdir, uiname)))


def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        Test_Main,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
