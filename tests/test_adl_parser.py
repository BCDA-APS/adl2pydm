
"""
simple unit tests for this package
"""

import logging
import os
import sys
import unittest

# turn off logging output
logging.basicConfig(level=logging.CRITICAL)

_test_path = os.path.dirname(__file__)
_path = os.path.join(_test_path, '..', 'src')
if _path not in sys.path:
    sys.path.insert(0, _path)

from adl2pydm import adl_parser


class Test_Files(unittest.TestCase):

    test_files = [
        "text_examples.adl",               # simple display
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
        "sampleWheel.adl",                 # image
        "scanDetPlot-R2-11-1.adl",         # cartesian plot, strip
        "sscan-R2-11-1-scanAux.adl",       # shell command
        "std-R3-5-ID_ctrl.adl",            # param
        "wheel_switch.adl",                # wheel switch
        # "beamHistory_full-R3-5.adl", # dl_color -- this .adl has content errors
        "ADBase-R3-3-1.adl",               # composite
        "simDetector-R3-3-31.adl",
        "userArrayCalc.adl",               # format="string"
        ]

    def setUp(self):
        self.path = os.path.dirname(__file__)
        self.medm_path = os.path.join(self.path, "medm")

    # def tearDown(self):
    #     pass

    def parseFile(self, short_name):
        full_name = os.path.join(self.medm_path, short_name)

        screen = adl_parser.MedmMainWidget()
        buf = screen.getAdlLines(full_name)
        screen.parseAdlBuffer(buf)
        return screen

    def assertEqualColor(self, color, r=None, g=None, b=None):
        if color is None:
            self.assertIsNone(r)
            self.assertIsNone(g)
            self.assertIsNone(b)
        else:
            self.assertIsInstance(color, adl_parser.Color)
            self.assertEqual(color.r, r)
            self.assertEqual(color.b, b)
            self.assertEqual(color.g, g)

    def assertEqualDictKeyValue(self, dictionary, key, value):
        self.assertIsInstance(dictionary, dict)
        self.assertIn(key, dictionary)
        self.assertEqual(dictionary[key], value)

    def assertEqualGeometry(self, parent, x, y, w, h):
        self.assertHasAttribute(parent, "geometry")
        geom = parent.geometry
        self.assertEqual(geom.x, x)
        self.assertEqual(geom.y, y)
        self.assertEqual(geom.width, w)
        self.assertEqual(geom.height, h)

    def assertEqualPoint(self, point, x, y):
        self.assertIsInstance(point, adl_parser.Point)
        self.assertEqual(point.x, x)
        self.assertEqual(point.y, y)

    def assertEqualTitle(self, parent, title):
        self.assertHasAttribute(parent, "title")
        self.assertEqual(parent.title, title)

    def assertHasAttribute(self, parent, attr_name):
        self.assertTrue(hasattr(parent, attr_name))

    def pickWidget(self, parent, num_widgets, n, symbol, line_offset):
        self.assertHasAttribute(parent, "widgets")
        self.assertEqual(len(parent.widgets), num_widgets)
        w = parent.widgets[n]
        self.assertEqual(w.symbol, symbol)
        self.assertEqual(w.line_offset, line_offset)
        return w

    # -------------------------------------------------

    def test__paths(self):
        self.assertTrue(os.path.exists(self.path))
        self.assertTrue(os.path.exists(self.medm_path))

    def test_adl_parser(self):
        for fname in self.test_files:
            screen = adl_parser.MedmMainWidget()
            self.assertEqual(screen.line_offset, 1)

            full_name = os.path.join(self.medm_path, fname)
            self.assertTrue(os.path.exists(full_name))

            buf = screen.getAdlLines(full_name)
            # any useful MEDM file has more than 10 lines
            self.assertGreater(len(buf), 10)

            screen.parseAdlBuffer(buf)
            self.assertGreater(len(screen.widgets), 0)

    # -------------------------------------------------

    def test_parse_medm_file(self):
        screen = self.parseFile("std-R3-5-ID_ctrl.adl")

        self.assertEqualGeometry(screen, 10, 10, 290, 310)
        self.assertEqualColor(screen.color, 0, 0, 0)
        self.assertEqualColor(screen.background_color, 212, 219, 157)
        self.assertEqual(screen.adl_filename, '/home/oxygen16/MOHAN/user_adl/ID_ctrl.adl')
        self.assertEqual(screen.adl_version, "020199")
        self.assertEqual(screen.cmap, "")
        self.assertEqual(len(screen.color_table), 65)
        self.assertEqualColor(screen.color_table[0], 255, 255, 255)
        self.assertEqualColor(screen.color_table[1], 236, 236, 236)
        self.assertEqualColor(screen.color_table[25], 88, 147, 255)
        self.assertEqualColor(screen.color_table[-1], 26, 115, 9)
        self.assertEqual(screen.line_offset, 1)
        self.assertEqual(screen.symbol, None)
        self.assertEqualTitle(screen, None)

        screen = self.parseFile("beamHistory_full-R3-5.adl")

        self.assertEqualGeometry(screen, 10, 10, 500, 650)
        self.assertEqualColor(screen.color, 0, 0, 0)
        self.assertEqualColor(screen.background_color, 212, 219, 157)
        self.assertEqual(screen.adl_filename, '/net/epics/xfd/WWW/xfd/operations/SR_Status.adl')
        self.assertEqual(screen.adl_version, "020199")
        self.assertEqual(screen.cmap, "")
        self.assertEqual(len(screen.color_table), 65)
        self.assertEqualColor(screen.color_table[0], 255, 255, 255)
        self.assertEqualColor(screen.color_table[1], 236, 236, 236)
        self.assertEqualColor(screen.color_table[25], 88, 147, 255)
        self.assertEqualColor(screen.color_table[-1], 26, 115, 9)
        self.assertEqual(screen.line_offset, 1)
        self.assertEqual(screen.symbol, None)
        self.assertEqualTitle(screen, None)

    # -------------------------------------------------

    def test_parse_medm_widget_arc(self):
        screen = self.parseFile("sampleWheel.adl")
        w = self.pickWidget(screen, 197, 2, "arc", 111)

        self.assertEqualGeometry(w, 436, 158, 40, 40)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 216, 0)
        self.assertEqualColor(w.background_color, None)

        self.assertTrue(hasattr(w, "contents"))
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 4)
        self.assertEqualDictKeyValue(w.contents, "beginAngle", 0.0)
        self.assertEqualDictKeyValue(w.contents, "pathAngle", 360.0)

        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 2)
        self.assertEqualDictKeyValue(attr, "fill", "outline")
        self.assertEqualDictKeyValue(attr, "width", "5")

        self.assertIn("dynamic attribute", w.contents)
        attr = w.contents["dynamic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 3)
        self.assertEqualDictKeyValue(attr, "calc", "A=3")
        self.assertEqualDictKeyValue(attr, "chan", "$(P)sample")
        self.assertEqualDictKeyValue(attr, "vis", "calc")

    def test_parse_medm_widget_bar(self):
        screen = self.parseFile("mca-R7-7-mca.adl")
        w = self.pickWidget(screen, 86, 84, "bar", 1779)

        self.assertEqualGeometry(w, 6, 217, 60, 16)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 255, 255, 255)
        self.assertEqualColor(w.background_color, 0, 0, 0)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)
        self.assertEqualDictKeyValue(w.contents, "clrmod", "alarm")
        self.assertEqualDictKeyValue(w.contents, "limits", "")
        self.assertIn("monitor", w.contents)
        monitor = w.contents["monitor"]
        self.assertEqual(len(monitor), 1)
        self.assertEqualDictKeyValue(monitor, "chan", "$(P)$(M).IDTIM")

    def test_parse_medm_widget_byte(self):
        screen = self.parseFile("optics-R2-13-1-pf4more.adl")
        w = self.pickWidget(screen, 79, 41, "byte", 754)

        self.assertEqualGeometry(w, 166, 224, 10, 336)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 139, 26, 150)
        self.assertEqualColor(w.background_color, 218, 218, 218)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 4)
        self.assertEqualDictKeyValue(w.contents, "direction", "down")
        self.assertEqualDictKeyValue(w.contents, "ebit", "15")
        self.assertEqualDictKeyValue(w.contents, "sbit", "0")
        self.assertIn("monitor", w.contents)
        monitor = w.contents["monitor"]
        self.assertEqual(len(monitor), 1)
        self.assertEqualDictKeyValue(monitor, "chan", "$(P)$(H)bitFlag$(A)")

    def test_parse_medm_widget_byte_additional(self):
        # see: https://github.com/BCDA-APS/adl2pydm/issues/32
        screen = self.parseFile("byte-monitor.adl")
        w = self.pickWidget(screen, 4, 0, "byte", 90)
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertNotIn("direction", w.contents)
        self.assertNotIn("ebit", w.contents)
        self.assertEqualDictKeyValue(w.contents, "sbit", "3")

        w = self.pickWidget(screen, 4, 1, "byte", 104)
        self.assertEqualDictKeyValue(w.contents, "ebit", "3")
        self.assertEqualDictKeyValue(w.contents, "sbit", "0")

        w = self.pickWidget(screen, 4, 2, "byte", 119)
        self.assertEqualDictKeyValue(w.contents, "direction", "down")
        self.assertNotIn("ebit", w.contents)
        self.assertEqualDictKeyValue(w.contents, "sbit", "3")

        w = self.pickWidget(screen, 4, 3, "byte", 134)
        self.assertEqualDictKeyValue(w.contents, "direction", "down")
        self.assertEqualDictKeyValue(w.contents, "ebit", "3")
        self.assertEqualDictKeyValue(w.contents, "sbit", "0")

    def test_parse_medm_widget_cartesian_plot(self):
        screen = self.parseFile("beamHistory_full-R3-5.adl")
        w = self.pickWidget(screen, 47, 13, "cartesian plot", 551)

        self.assertEqualGeometry(w, 11, 281, 480, 200)
        self.assertEqualTitle(w, "")
        self.assertEqualColor(w.color, 10, 0, 184)
        self.assertEqualColor(w.background_color, 218, 218, 218)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 13)
        self.assertEqualDictKeyValue(w.contents, "count", "1")
        self.assertEqualDictKeyValue(w.contents, "erase", "")
        self.assertEqualDictKeyValue(w.contents, "eraseMode", "if not zero")
        self.assertEqualDictKeyValue(w.contents, "erase_oldest", "plot last n pts")
        self.assertEqualDictKeyValue(w.contents, "style", "fill-under")
        self.assertEqualDictKeyValue(w.contents, "trigger", "")
        self.assertEqualDictKeyValue(w.contents, "xlabel", "History (Hours)")
        self.assertEqualDictKeyValue(w.contents, "ylabel", "Current")

        symbol = "x_axis"
        self.assertIn(symbol, w.contents)
        axis = w.contents[symbol]
        self.assertEqual(len(axis), 4)
        self.assertEqualDictKeyValue(axis, "axisStyle", "linear")
        self.assertEqualDictKeyValue(axis, "maxRange", "1.000000")
        self.assertEqualDictKeyValue(axis, "minRange", "0.000000")
        self.assertEqualDictKeyValue(axis, "rangeStyle", "auto-scale")

        symbol = "y1_axis"
        self.assertIn(symbol, w.contents)
        axis = w.contents[symbol]
        self.assertEqual(len(axis), 4)
        self.assertEqualDictKeyValue(axis, "axisStyle", "linear")
        self.assertEqualDictKeyValue(axis, "maxRange", "1.000000")
        self.assertEqualDictKeyValue(axis, "minRange", "0.000000")
        self.assertEqualDictKeyValue(axis, "rangeStyle", "auto-scale")

        symbol = "y2_axis"
        self.assertIn(symbol, w.contents)
        axis = w.contents[symbol]
        self.assertEqual(len(axis), 4)
        self.assertEqualDictKeyValue(axis, "axisStyle", "linear")
        self.assertEqualDictKeyValue(axis, "maxRange", "1.000000")
        self.assertEqualDictKeyValue(axis, "minRange", "0.000000")
        self.assertEqualDictKeyValue(axis, "rangeStyle", "from channel")

        self.assertIn("traces", w.contents)
        traces = w.contents["traces"]
        self.assertIsInstance(traces, list)
        self.assertEqual(len(traces), 8)
        for item, trace in enumerate(traces):
            self.assertEqual(len(trace), 3)
            self.assertIn("color", trace)
            if item == 0:
                xdata = "S:SRtimeCP"
                ydata = "S:SRcurrentCP"
                r, g, b = 42, 99, 228
            else:
                xdata = ""
                ydata = ""
                r, g, b = 0, 0, 0
            self.assertEqualDictKeyValue(trace, "xdata", xdata)
            self.assertEqualDictKeyValue(trace, "ydata", ydata)
            self.assertEqualColor(trace["color"], r, g, b)

    def test_parse_medm_widget_choice_button(self):
        screen = self.parseFile("motorx-R6-10-1.adl")
        w = self.pickWidget(screen, 31, 30, "choice button", 568)

        self.assertEqualGeometry(w, 45, 137, 71, 20)
        self.assertEqualTitle(w, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertEqualDictKeyValue(w.contents, "stacking", "column")

        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "chan", "$(P)$(M).SET")

    def test_parse_medm_widget_composite(self):
        screen = self.parseFile("ADBase-R3-3-1.adl")
        w = self.pickWidget(screen, 10, 1, "composite", 101)

        self.assertEqualGeometry(w, 6, 35, 350, 340)
        self.assertEqualColor(w.color, None)
        self.assertEqualColor(w.background_color, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertEqualDictKeyValue(w.contents, "composite file", "ADSetup.adl")
        self.assertEqualDictKeyValue(w.contents, "composite name", "")

    # TODO: embedded display : no example in synApps

    def test_parse_medm_widget_image(self):
        screen = self.parseFile("sampleWheel.adl")
        w = self.pickWidget(screen, 197, 1, "image", 101)

        self.assertEqualGeometry(w, 0, 20, 500, 500)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, None)
        self.assertEqualColor(w.background_color, None)

        self.assertTrue(hasattr(w, "contents"))
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertEqualDictKeyValue(w.contents, "image name", "sampleWheel.gif")
        self.assertEqualDictKeyValue(w.contents, "type", "gif")

    def test_parse_medm_widget_indicator(self):
        screen = self.parseFile("optics-R2-13-1-CoarseFineMotorShow.adl")
        w = self.pickWidget(screen, 12, 5, "indicator", 156)

        self.assertEqualGeometry(w, 178, 52, 250, 25)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 115, 223, 255)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)

        # self.assertEqualDictKeyValue(w.contents, "beginAngle", 0.0)
        # self.assertEqualDictKeyValue(w.contents, "pathAngle", 360.0)
        self.assertIn("monitor", w.contents)
        monitor = w.contents["monitor"]
        self.assertEqual(len(monitor), 1)
        self.assertEqualDictKeyValue(monitor, "chan", "$(PM)$(CM).RBV")

    def test_parse_medm_widget_menu(self):
        screen = self.parseFile("motorx_all-R6-10-1.adl")
        w = self.pickWidget(screen, 175, 23, "composite", 417)
        w = self.pickWidget(w, 2, 0, "menu", 417)

        self.assertEqualGeometry(w, 186, 232, 100, 18)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 115, 223, 255)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 1)

        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertIsInstance(control, dict)
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "chan", "$(P)$(M).FOFF")

    def test_parse_medm_widget_message_button(self):
        screen = self.parseFile("std-R3-5-ID_ctrl.adl")
        w = self.pickWidget(screen, 25, 3, "message button", 434)

        self.assertEqualGeometry(w, 150, 220, 140, 40)
        self.assertEqualTitle(w, "Stop ")
        self.assertEqualColor(w.color, 253, 0, 0)
        self.assertEqualColor(w.background_color, 160, 18, 7)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 5)
        self.assertEqualDictKeyValue(w.contents, "clrmod", "static")
        self.assertEqualDictKeyValue(w.contents, "press_msg", "1")
        self.assertEqualDictKeyValue(w.contents, "release_msg", "")

        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertIsInstance(control, dict)
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "ctrl", "ID$(xx):UN:stopSQ.PROC")

    def test_parse_medm_widget_meter(self):
        screen = self.parseFile("calc-R3-7-userCalcMeter.adl")
        w = self.pickWidget(screen, 6, 0, "meter", 87)

        self.assertEqualGeometry(w, 0, 38, 200, 150)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 218, 218, 218)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 1)
        self.assertIn("monitor", w.contents)
        monitor = w.contents["monitor"]
        self.assertEqual(len(monitor), 1)
        self.assertEqualDictKeyValue(monitor, "chan", "$(P)$(C).VAL")

    def test_parse_medm_widget_oval(self):
        screen = self.parseFile("motorx_all-R6-10-1.adl")
        w = self.pickWidget(screen, 175, 60, "oval", 993)

        self.assertEqualGeometry(w, 290, 132, 21, 21)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 253, 0, 0)
        self.assertEqualColor(w.background_color, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 0)
        self.assertIn("dynamic attribute", w.contents)
        attr = w.contents["dynamic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 2)
        self.assertEqualDictKeyValue(attr, "chan", "$(P)$(M).LLS")
        self.assertEqualDictKeyValue(attr, "vis", "if not zero")

    def test_parse_medm_widget_polygon(self):
        screen = self.parseFile("calc-R3-7-1-FuncGen_full.adl")
        w = self.pickWidget(screen, 38, 18, "composite", 337)
        w = self.pickWidget(w, 2, 1, "polygon", 353)

        self.assertEqualGeometry(w, 260, 174, 10, 10)
        self.assertEqualTitle(w, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 1)
        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 0)

        self.assertHasAttribute(w, "points")
        self.assertEqual(len(w.points), 4)
        self.assertEqualPoint(w.points[0], 260, 174)
        self.assertEqualPoint(w.points[1], 270, 178)
        self.assertEqualPoint(w.points[2], 260, 184)
        self.assertEqualPoint(w.points[3], 260, 174)

    def test_parse_medm_widget_polyline(self):
        screen = self.parseFile("calc-R3-7-1-FuncGen_full.adl")
        w = self.pickWidget(screen, 38, 18, "composite", 337)
        w = self.pickWidget(w, 2, 0, "polyline", 337)

        self.assertEqualGeometry(w, 120, 178, 142, 2)
        self.assertEqualTitle(w, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 1)
        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertIsInstance(attr, dict)
        self.assertEqual(len(attr), 1)
        self.assertEqualDictKeyValue(attr, "width", "2")

        self.assertHasAttribute(w, "points")
        self.assertEqual(len(w.points), 2)
        self.assertEqualPoint(w.points[0], 121, 179)
        self.assertEqualPoint(w.points[1], 261, 179)

    def test_parse_medm_widget_rectangle(self):
        screen = self.parseFile("ADBase-R3-3-1.adl")
        w = self.pickWidget(screen, 10, 0, "rectangle", 90)

        self.assertEqualGeometry(w, 0, 4, 715, 25)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 218, 218, 218)
        self.assertEqualColor(w.background_color, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 1)
        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertEqual(len(attr), 0)

    def test_parse_medm_widget_related_display(self):
        screen = self.parseFile("std-R3-5-ID_ctrl.adl")
        w = self.pickWidget(screen, 25, 13, "related display", 611)

        self.assertEqualGeometry(w, 119, 285, 18, 18)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 88, 52, 15)
        self.assertEqualColor(w.background_color, 115, 223, 255)

        self.assertIsInstance(w.displays, list)
        self.assertEqual(len(w.displays), 8)
        display = w.displays[0]
        self.assertIsInstance(display, dict)
        self.assertEqualDictKeyValue(display, "args", "xx=$(xx)")
        self.assertEqualDictKeyValue(display, "label", "Taper Control")
        self.assertEqualDictKeyValue(display, "name", "ID_taper_ctrl.adl")

    def test_parse_medm_widget_shell_command(self):
        screen = self.parseFile("sscan-R2-11-1-scanAux.adl")
        w = self.pickWidget(screen, 66, 42, "shell command", 725)

        self.assertEqualGeometry(w, 350, 239, 20, 20)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 251, 243, 74)

        self.assertHasAttribute(w, "contents")
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 0)

        self.assertHasAttribute(w, "commands")
        self.assertIsInstance(w.commands, list)
        self.assertEqual(len(w.commands), 1)
        cmd = w.commands[0]
        self.assertIsInstance(cmd, dict)
        self.assertEqual(len(cmd), 2)
        self.assertEqualDictKeyValue(cmd, "label", "Help")
        self.assertEqualDictKeyValue(cmd, "name", "medm_help.sh &T")

    def test_parse_medm_widget_strip_chart(self):
        screen = self.parseFile("calc-R3-7-1-FuncGen_full.adl")
        # this widget is in a composite
        w = self.pickWidget(screen, 38, 32, "composite", 614)
        w = self.pickWidget(w, 1, 0, "strip chart", 614)

        self.assertEqualGeometry(w, 0, 260, 450, 170)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 255, 255, 255)

        self.assertHasAttribute(w, "contents")
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)
        self.assertEqualDictKeyValue(w.contents, "period", "1.000000")
        self.assertEqualDictKeyValue(w.contents, "units", "minute")
        pens = w.contents.get("pens")
        self.assertIsNotNone(pens)
        self.assertEqual(len(pens), 2)
        self.assertEqual(pens[0]["chan"], "$(P)$(Q):Output")
        self.assertEqual(pens[1]["chan"], "$(P)$(Q):Readback")
        self.assertEqualColor(pens[0]["color"], 0, 0, 0)
        self.assertEqualColor(pens[1]["color"], 253, 0, 0)

    def test_parse_medm_widget_text(self):
        screen = self.parseFile("ADBase-R3-3-1.adl")
        w = self.pickWidget(screen, 10, 9, "text", 181)

        self.assertEqualGeometry(w, 0, 5, 715, 25)
        self.assertEqualTitle(w, "Area Detector Control - $(P)$(R)")
        self.assertEqualColor(w.color, 10, 0, 184)
        self.assertEqualColor(w.background_color, None)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertEqualDictKeyValue(w.contents, "align", "horiz. centered")
        self.assertIn("basic attribute", w.contents)
        attr = w.contents["basic attribute"]
        self.assertEqual(len(attr), 0)

    def test_parse_medm_widget_text_entry(self):
        screen = self.parseFile("std-R3-5-ID_ctrl.adl")
        w = self.pickWidget(screen, 25, 8, "text entry", 531)

        self.assertEqualGeometry(w, 54, 114, 120, 38)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 255, 255, 255)
        self.assertEqualColor(w.background_color, 10, 0, 184)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)
        self.assertEqualDictKeyValue(w.contents, "format", "decimal")
        self.assertEqualDictKeyValue(w.contents, "clrmod", "static")

        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertIsInstance(control, dict)
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "ctrl", "ID$(xx):UN:setavgAI.VAL")

    def test_parse_medm_widget_text_update(self):
        screen = self.parseFile("text_examples.adl")
        w = self.pickWidget(screen, 17, 0, "text update", 90)

        self.assertEqualGeometry(w, 10, 46, 140, 24)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 187, 187, 187)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 2)
        self.assertEqualDictKeyValue(w.contents, "limits", "")

        self.assertIn("monitor", w.contents)
        mon = w.contents["monitor"]
        self.assertIsInstance(mon, dict)
        self.assertEqual(len(mon), 1)
        self.assertEqualDictKeyValue(mon, "chan", "$(P)")

    def test_parse_medm_widget_valuator(self):
        screen = self.parseFile("optics-R2-13-xiahsc.adl")
        w = self.pickWidget(screen, 55, 8, "valuator", 201)

        self.assertEqualGeometry(w, 52, 247, 100, 20)
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)
        self.assertEqualDictKeyValue(w.contents, "dPrecision", "0.010000")
        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "chan", "$(P)$(HSC)l")
        self.assertEqualTitle(w, None)

    def test_parse_medm_widget_wheel_switch(self):
        screen = self.parseFile("wheel_switch.adl")
        w = self.pickWidget(screen, 1, 0, "wheel switch", 90)

        self.assertEqualGeometry(w, 19, 16, 185, 91)
        self.assertEqualTitle(w, None)
        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 7)
        self.assertEqualDictKeyValue(w.contents, "hoprSrc", "default")
        self.assertEqualDictKeyValue(w.contents, "loprSrc", "default")
        self.assertEqualDictKeyValue(w.contents, "precSrc", "default")
        self.assertEqualDictKeyValue(w.contents, "hoprDefault", "10")
        self.assertEqualDictKeyValue(w.contents, "loprDefault", "-10")
        self.assertEqualDictKeyValue(w.contents, "precDefault", "3")
        control = w.contents["control"]
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "chan", "sky:userCalc2.A")

    def test_parse_medm_userArrayCalc(self):
        screen = self.parseFile("userArrayCalc.adl")
        w = self.pickWidget(screen, 88, 24, "text entry", 442)

        self.assertEqualGeometry(w, 235, 170, 150, 20)
        self.assertEqualTitle(w, None)
        self.assertEqualColor(w.color, 0, 0, 0)
        self.assertEqualColor(w.background_color, 115, 223, 255)

        self.assertIsInstance(w.contents, dict)
        self.assertEqual(len(w.contents), 3)
        self.assertEqualDictKeyValue(w.contents, "format", "string")
        self.assertEqualDictKeyValue(w.contents, "limits", "")

        self.assertIn("control", w.contents)
        control = w.contents["control"]
        self.assertIsInstance(control, dict)
        self.assertEqual(len(control), 1)
        self.assertEqualDictKeyValue(control, "chan", "$(P)$(C).AA")


def suite(*args, **kw):
    test_suite = unittest.TestSuite()
    test_list = [
        Test_Files,
        ]
    for test_case in test_list:
        test_suite.addTest(unittest.makeSuite(test_case))
    return test_suite


if __name__ == "__main__":
    runner=unittest.TextTestRunner()
    runner.run(suite())
