#!/usr/bin/env python

"""
read the MEDM .adl file into Python data structures

Parse the file by blocks.
Only rely on packages in the standard Python distribution. 

MEDM's .adl files are divided into a list of blocks where 
each block is structured thus::

    symbol {
        contents
    }

The symbol is given without double quotes if it has not
embedded white space.  Otherwise, double quotes surround the
symbol.

The *contents* are a list of block(s) and assignment(s) or values.
An *assignment* is structured:  ``symbol=value``
A *value* is a number, text surrounded by double quotes, 
or a list of values surrounded by parentheses.

Three special blocks come at the start of the MEDM file: 
file, display, and "color map".  The remaining blocks at 
the main screen level (0) correspond to GUI widgets or, in the case of 
*composite*, a list of widgets that are grouped.

Other blocks are used to provide configuration for their 
parent GUI widget.
"""

from collections import defaultdict, namedtuple, OrderedDict
import logging
import os

import adl_symbols


TEST_FILES = [
    "screens/medm/newDisplay.adl",                  # simple display
    "screens/medm/xxx-R5-8-4.adl",                  # related display
    "screens/medm/xxx-R6-0.adl",
    # FIXME: needs more work here (unusual structure, possibly stress test):  "screens/medm/base-3.15.5-caServerApp-test.adl",# info[, "<<color rules>>", "<<color map>>"
    "screens/medm/calc-3-4-2-1-FuncGen_full.adl",   # strip chart
    "screens/medm/calc-R3-7-1-FuncGen_full.adl",    # strip chart
    "screens/medm/calc-R3-7-userCalcMeter.adl",     # meter
    "screens/medm/mca-R7-7-mca.adl",                # bar
    "screens/medm/motorx-R6-10-1.adl",
    "screens/medm/motorx_all-R6-10-1.adl",
    "screens/medm/optics-R2-13-1-CoarseFineMotorShow.adl",  # indicator
    "screens/medm/optics-R2-13-1-kohzuGraphic.adl", # image
    "screens/medm/optics-R2-13-1-pf4more.adl",      # byte
    "screens/medm/optics-R2-13-xiahsc.adl",         # valuator
    "screens/medm/scanDetPlot-R2-11-1.adl",         # cartesian plot, strip
    "screens/medm/sscan-R2-11-1-scanAux.adl",       # shell command
    "screens/medm/std-R3-5-ID_ctrl.adl",            # param
    # "screens/medm/beamHistory_full-R3-5.adl", # dl_color -- this .adl has content errors
    "screens/medm/ADBase-R3-3-1.adl",               # composite
    "screens/medm/simDetector-R3-3-31.adl",
    ]

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


"""a color used in MEDM"""
Color = namedtuple('Color', 'r g b')

"""MEDM's object block contains the widget geometry"""
Geometry = namedtuple('Geometry', 'x y width height')

"""MEDM's points item: points = [Point]"""
Point = namedtuple('Point', 'x y')


class Block(object):
    """ADL file block structure"""
    
    def __init__(self, start, end, level, symbol):
        self.start = start
        self.end = end
        self.level = level
        self.symbol = symbol
    
    def __str__(self):
        fmt = "Block: %d:%d:%d %s"
        return fmt % (self.level, self.start, self.end, str(self.symbol))


class MedmBaseWidget(object):
    
    def __init__(self):
        self.background_color = None
        self.color = None
        self.geometry = None
        self.line_offset = 0
        self.symbol = None
        self.title = None
    
    def __str__(self):
        fmt = "Widget(%s)"
        args = []
        if self.title is not None:
            args.append("title=\"%s\"" % str(self.title))
        if self.symbol is not None:
            args.append("symbol=\"%s\"" % str(self.symbol))
        args.append("line=%d" % self.line_offset)
        return fmt % ", ".join(args)
    
    def getNamedBlock(self, block_name, blocks):
        """
        """
        block = [b for b in blocks if b.symbol == block_name]
        if len(block) > 0:
            return block[0]

    def locateAssignments(self, buf):
        """
        identify and record the line number of all assignments in the buffer at this nesting level
        """
        assignments = OrderedDict()
        level = 0
        nesting = level # remember nesting, identify assignments only at THIS level
        for line, text in enumerate(buf):
            p = text.find("=")
            if text.rstrip().endswith(" {"):
                nesting += 1
            elif text.rstrip().endswith("}"):
                nesting -= 1
            elif nesting == level and p > 0:
                key = text[:p].strip()
                value = text[p+1:].strip().strip('"')
                # TODO: look for parentheses
                assignments[key] = value
        return assignments
    
    def locateBlocks(self, buf):
        """
        identify and record the start and end of all blocks at this nesting level in the buffer
        """
        blocks = []
        level = 0
        nesting = level
        for line, text in enumerate(buf):
            if text.rstrip().endswith(" {"):
                if nesting == level:
                    symbol = text.strip()[:-2]
                    block = Block(line, None, nesting, symbol.strip('"'))
                nesting += 1
            elif text.rstrip().endswith("}"):
                nesting -= 1
                if nesting == level:
                    block.end = line
                    blocks.append(block)
        return blocks
    
    def parseAdlBuffer(self, buf):
        """generic handling, override as needed"""
        assignments = self.locateAssignments(buf)
        blocks = self.locateBlocks(buf)
        text = "".join(buf)

        # assign certain items in named attributes
        assignments = self.parseColorAssignments(assignments)
            
        # all widget blocks have an "object"
        block = self.getNamedBlock("object", blocks)
        if block is not None:
            self.geometry = self.parseObjectBlock(buf[block.start+1:block.end])
            
            # remove that block
            for i, b in enumerate(blocks):
                if b.symbol == "object":
                    break
            del blocks[i]
        
        # stash remaining contents
        contents = dict(**assignments)
        for block in blocks:            # TODO: improve
            contents[block.symbol] = "".join(buf[block.start+1:block.end])
        self.contents = contents

        if "label" in assignments:
            self.title = assignments["label"]
            del self.contents["label"], assignments["label"]

        for symbol in ("basic attribute", "dynamic attribute", "control", "monitor", "param"):
            block = self.getNamedBlock(symbol, blocks)
            if block is not None:
                aa = self.locateAssignments(buf[block.start+1:block.end])
                aa = self.parseColorAssignments(aa)
                self.contents[symbol] = aa

        block = self.getNamedBlock("points", blocks)
        if block is not None:
            points = []
            for pair in buf[block.start+1:block.end]:
                x, y = map(int, pair.replace("(", "").replace(")", "").split(","))
                points.append(Point(x, y))
            self.points = points

        return assignments, blocks
    
    def parseChildren(self, main, blocks, buf):
        xref = {
            "arc" : MedmArcWidget,
            "bar" : MedmBarWidget,
            "byte" : MedmByteWidget,
            "cartesian plot" : MedmCartesianPlotWidget,
            "choice button" : MedmChoiceButtonWidget,
            "composite" : MedmCompositeWidget,
            "embedded display" : MedmEmbeddedDisplayWidget,
            "image" : MedmImageWidget,
            "indicator" : MedmIndicatorWidget,
            "menu" : MedmMenuWidget,
            "message button" : MedmMessageButtonWidget,
            "meter" : MedmMeterWidget,
            "oval" : MedmOvalWidget,
            "polygon" : MedmPolygonWidget,
            "polyline" : MedmPolylineWidget,
            "rectangle" : MedmRectangleWidget,
            "related display" : MedmRelatedDisplayWidget,
            "shell command" : MedmShellCommandWidget,
            "strip chart" : MedmStripChartWidget,
            "text" : MedmTextWidget,
            "text entry" : MedmTextEntryWidget,
            "text update" : MedmTextUpdateWidget,
            "valuator" : MedmValuatorWidget,
            "wheel switch" : MedmWheelSwitchWidget,
            }
        for block in blocks:
            if block.symbol in adl_symbols.widgets:
                logger.debug("Processing %s block" % block.symbol)
                widget_handler = xref.get(block.symbol, MedmGenericWidget)
                widget = widget_handler(self.line_offset+block.start, main, block.symbol)
                widget.parseAdlBuffer(buf[block.start+1:block.end])
                self.widgets.append(widget)
    
    def parseColorAssignments(self, assignments):
        # assign certain items in named attributes
        xref = dict(clr="color", bclr="background_color")
        if hasattr(self, "color_table"):
            clut = self.color_table
        else:
            clut = self.main.color_table    # Color LookUp Table
        for k, sk in xref.items():
            value = assignments.get(k)
            if value is not None:
                self.__setattr__(sk, clut[int(value)])  # FIXME: caServerApp/test.adl fails here with IndexError
                del assignments[k]
        return assignments
    
    def parseObjectBlock(self, buf):
        """MEDM "object" block defines a Geometry for its parent"""
        a = self.locateAssignments(buf)
        arr = map(int, (a["x"], a["y"], a["width"], a["height"]))   # convert to int
        return Geometry(*list(arr))


class MedmMainWidget(MedmBaseWidget):
    
    def __init__(self, given_filename=None):
        MedmBaseWidget.__init__(self)
        self.given_filename = given_filename    # file name as provided
        self.adl_filename = "unknown"   # file name given in the file
        self.adl_version = "unknown"    # file version given in the file
        self.color_table = []           # TODO: supply a default color table
        self.widgets = []
        self.line_offset = 1            # line numbers start at 1
    
    def getAdlLines(self, fname=None):
        fname = fname or self.given_filename
        if not os.path.exists(fname):
            msg = "Could not find file: " + fname
            raise ValueError(msg)
        self.given_filename = fname
        with open(fname, "r") as fp:
            return fp.readlines()

    def parseAdlBuffer(self, buf):
        logger.debug("\n"*2)
        logger.debug(self.given_filename)
        blocks = self.locateBlocks(buf)
        logger.debug("\n".join(map(str,blocks)))
        
        xref = OrderedDict([
            ("file", self.parseFileBlock),
            ("color map", self.parseColorMapBlock), # must BEFORE display
            ("display", self.parseDisplayBlock),
        ])
        for symbol, handler in xref.items():
            block = self.getNamedBlock(symbol, blocks)
            if block is None:
                logger.warn("Did not find %s block" % symbol)
            else:
                logger.debug("Processing %s block" % symbol)
                handler(buf[block.start+1:block.end])
         
        # sift out the three block types already handled
        blocks = [block for block in blocks if block.symbol in adl_symbols.widgets]
        self.parseChildren(self, blocks, buf)
    
    def parseFileBlock(self, buf):
        # TODO: keep original line numbers for debug purposes
        xref = dict(name="adl_filename", version="adl_version")
        assignments = self.locateAssignments(buf)
        for k, sk in xref.items():
            value = assignments.get(k)
            if value is not None:
                self.__setattr__(sk, value)
    
    def parseColorMapBlock(self, buf):
        """read the color_table (clut) from the "color map"""
        # TODO: keep original line numbers for debug purposes
        assignments = self.locateAssignments(buf)   # ignore ncolors=
        blocks = self.locateBlocks(buf)

        block = self.getNamedBlock("colors", blocks)
        if block is not None:
            # list of RGB 2-digit hex strings: RRGGBB
            def _parse_colors_(rgbhex):
                r = int(rgbhex[:2], 16)
                g = int(rgbhex[2:4], 16)
                b = int(rgbhex[4:6], 16)
                return Color(r, g, b)

            text = "".join(buf[block.start+1:block.end])
            clut = map(_parse_colors_, text.replace(",", " ").split())
            self.color_table = list(clut)
        else:
            # dl_color blocks  contain assignments: r, g, b inten
            block = self.getNamedBlock("dl_color", blocks)
            if block is not None:
                clut = []
                for block in blocks:
                    a = self.locateAssignments(buf[block.start+1:block.end])
                    arr = map(int, (a["r"], a["g"], a["b"]))
                    color = Color(*list(arr))   # ignore inten (default = 255)
                    clut.append(color)
                self.color_table = clut
    
    def parseDisplayBlock(self, buf):
        # TODO: keep original line numbers for debug purposes
        assignments = self.locateAssignments(buf)
        blocks = self.locateBlocks(buf)

        # assign certain items in named attributes
        assignments = self.parseColorAssignments(assignments)

        # assign remaining attributes
        for k, value in assignments.items():
            self.__setattr__(k, value)

        block = self.getNamedBlock("object", blocks)
        if block is not None:
            self.geometry = self.parseObjectBlock(buf[block.start+1:block.end])
        # ignore any other blocks


class MedmGenericWidget(MedmBaseWidget):
    
    debug = False
    
    def __init__(self, line, main, symbol):
        MedmBaseWidget.__init__(self)
        self.line_offset = line
        self.main = main
        self.symbol = symbol

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)
        if self.debug:
            _debug = self.debug


class MedmArcWidget(MedmGenericWidget): pass
class MedmBarWidget(MedmGenericWidget): pass
class MedmByteWidget(MedmGenericWidget): pass


class MedmCartesianPlotWidget(MedmGenericWidget):
    
    def __init__(self, line, main, symbol):
        MedmGenericWidget.__init__(self, line, main, symbol)
        self.traces = []

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        traces = {}
        for block in blocks:
            if not block.symbol.startswith("trace["):
                continue
            del self.contents[block.symbol]
            aa = self.locateAssignments(buf[block.start+1:block.end])
            clr = aa.get("data_clr")
            if clr is not None:
                del aa["data_clr"]
                aa["color"] = self.main.color_table[int(clr)]
            row = block.symbol.replace("[", " ").replace("]", "").split()[-1]
            traces[row] = aa
        
        def sorter(value):
            return int(value)
        self.traces = [traces[k] for k in sorted(traces.keys(), key=sorter)]


class MedmChoiceButtonWidget(MedmGenericWidget): pass


class MedmCompositeWidget(MedmBaseWidget):
    """contains other widgets or an entire .adl screen"""
    
    def __init__(self, line, main, symbol):
        MedmBaseWidget.__init__(self)
        self.line_offset = line
        self.main = main
        self.symbol = symbol        # "composite"
        self.widgets = []

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)
        
        block = self.getNamedBlock("children", blocks)
        if block is not None:
            aa = self.locateAssignments(buf[block.start+1:block.end])
            bb = self.locateBlocks(buf[block.start+1:block.end])
            self.parseChildren(self.main, bb, buf[block.start+1:block.end])


class MedmEmbeddedDisplayWidget(MedmGenericWidget): debug = True # TODO: need example in .adl file!
class MedmImageWidget(MedmGenericWidget): pass
class MedmIndicatorWidget(MedmGenericWidget): pass
class MedmMenuWidget(MedmGenericWidget): pass
class MedmMessageButtonWidget(MedmGenericWidget): pass
class MedmMeterWidget(MedmGenericWidget): pass
class MedmOvalWidget(MedmGenericWidget): pass
class MedmPolygonWidget(MedmGenericWidget): pass
class MedmPolylineWidget(MedmGenericWidget): pass
class MedmRectangleWidget(MedmGenericWidget): pass


class MedmRelatedDisplayWidget(MedmGenericWidget):
    
    def __init__(self, line, main, symbol):
        MedmGenericWidget.__init__(self, line, main, symbol)
        self.displays = []

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        displays = {}
        for block in blocks:
            if not block.symbol.startswith("display["):
                continue
            del self.contents[block.symbol]
            aa = self.locateAssignments(buf[block.start+1:block.end])
            row = block.symbol.replace("[", " ").replace("]", "").split()[-1]
            displays[row] = aa
        
        def sorter(value):
            return int(value)
        self.displays = [displays[k] for k in sorted(displays.keys(), key=sorter)]


class MedmShellCommandWidget(MedmGenericWidget):
    
    def __init__(self, line, main, symbol):
        MedmGenericWidget.__init__(self, line, main, symbol)
        self.commands = []

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        commands = {}
        for block in blocks:
            if not block.symbol.startswith("command["):
                continue
            del self.contents[block.symbol]
            aa = self.locateAssignments(buf[block.start+1:block.end])
            row = block.symbol.replace("[", " ").replace("]", "").split()[-1]
            commands[row] = aa
        
        def sorter(value):
            return int(value)
        self.commands = [commands[k] for k in sorted(commands.keys(), key=sorter)]


class MedmStripChartWidget(MedmGenericWidget):
    
    def __init__(self, line, main, symbol):
        MedmGenericWidget.__init__(self, line, main, symbol)
        self.pens = []

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        pens = {}
        for block in blocks:
            if not block.symbol.startswith("pen["):
                continue
            del self.contents[block.symbol]
            aa = self.locateAssignments(buf[block.start+1:block.end])
            clr = aa.get("clr")
            if clr is not None:
                del aa["clr"]
                aa["color"] = self.main.color_table[int(clr)]
            row = block.symbol.replace("[", " ").replace("]", "").split()[-1]
            pens[row] = aa
        
        def sorter(value):
            return int(value)
        self.pens = [pens[k] for k in sorted(pens.keys(), key=sorter)]


class MedmTextWidget(MedmGenericWidget):

    def parseAdlBuffer(self, buf):
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)
        if "textix" in assignments:
            self.title = assignments["textix"]
            del self.contents["textix"], assignments["textix"]


class MedmTextEntryWidget(MedmGenericWidget): pass
class MedmTextUpdateWidget(MedmGenericWidget): pass
class MedmValuatorWidget(MedmGenericWidget): pass
class MedmWheelSwitchWidget(MedmGenericWidget): debug = True # TODO: need example in .adl file!


if __name__ == "__main__":
    for fname in TEST_FILES:
        screen = MedmMainWidget()
        buf = screen.getAdlLines(fname)
        screen.parseAdlBuffer(buf)
    print("done")