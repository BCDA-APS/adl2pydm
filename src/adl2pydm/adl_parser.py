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

from collections import namedtuple, OrderedDict
import logging
import os

from . import symbols


logger = logging.getLogger(__name__)

"""a color used in MEDM"""
Color = namedtuple('Color', 'r g b')

"""MEDM's object block contains the widget geometry"""
Geometry = namedtuple('Geometry', 'x y width height')

"""MEDM's points item: points = [Point]"""
Point = namedtuple('Point', 'x y')

# Internally the angles are specified in integer 1/64-degree units.
MEDM_DEGREE_UNITS = 64.0


def deg_to_adl(deg):
    """
    Converts from degrees to MEDM degrees.

    1 deg = 64 MEDMdeg

    Parameters
    ----------
    deg : float
        The value to convert.

    Returns
    -------
    int
        The value converted.
    """
    # Angles for MEDM are in units of 1/64 of a degree
    return int(deg * MEDM_DEGREE_UNITS)


def adl_to_deg(deg):
    """
    Converts from MEDM degrees to degrees.

    1 deg = 64 MEDMdeg

    Parameters
    ----------
    deg : float, int, str
        The value to convert.

    Returns
    -------
    float
        The value converted.
    """
    # Angles for MEDM are in units of 1/64 of a degree
    return float(deg) / MEDM_DEGREE_UNITS


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
        self.medm_widget_handlers = {
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
                key = text[:p].strip().strip('"')
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

    def parseAdlBuffer(self, buf):              # lgtm [py/similar-function]
        """generic handling, override as needed"""
        assignments = self.locateAssignments(buf)
        blocks = self.locateBlocks(buf)

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

        reservedLabels = "channel limits outline none".split()
        reservedLabels.append("no decorations")
        label = assignments.get("label")
        if label is not None and label not in reservedLabels:
            self.title = label
            logger.debug(f"label={label}")

        # stash remaining contents
        contents = dict(**assignments)
        for block in blocks:            # TODO: improve
            contents[block.symbol] = "".join(buf[block.start+1:block.end])
        self.contents = contents

        limits = self.contents.get("limits", "").strip()
        if len(limits) > 0:
            for line in self.contents.pop("limits").splitlines():
                k, v = line.strip().split("=")
                self.contents[k] = v.strip('"')

        for symbol in ("basic attribute", "dynamic attribute", "control", "monitor", "param"):
            block = self.getNamedBlock(symbol, blocks)
            if block is not None:
                aa = self.locateAssignments(buf[block.start+1:block.end])
                aa = self.parseColorAssignments(aa)
                self.contents[symbol] = aa

        for angle_name in "begin path".split():
            if angle_name in self.contents:
                angle = self.contents.pop(angle_name)
                self.contents[angle_name + "Angle"] = adl_to_deg(angle)

        block = self.getNamedBlock("points", blocks)
        if block is not None:
            points = []
            for pair in buf[block.start+1:block.end]:
                x, y = map(int, pair.replace("(", "").replace(")", "").split(","))
                points.append(Point(x, y))
            self.points = points
            if "points" in self.contents:
                del self.contents["points"]

        return assignments, blocks

    def parseChildren(self, main, blocks, buf):
        for block in blocks:
            if block.symbol in symbols.adl_widgets:
                logger.debug("(#%d) %s" % (self.line_offset+block.start, block.symbol))
                handler = self.medm_widget_handlers.get(block.symbol, MedmGenericWidget)
                widget = handler(self.line_offset+block.start, main, block.symbol)
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
            if value is not None and value.isnumeric():
                # TODO: what if value="alarm" (file: flipRotate.adl)
                v = int(value)
                if len(clut) > v:
                    self.__setattr__(sk, clut[int(value)])
                    # FIXME: caServerApp/test.adl fails here with IndexError
                del assignments[k]
        return assignments

    def parseObjectBlock(self, buf):
        """MEDM "object" block defines a Geometry for its parent"""
        a = self.locateAssignments(buf)
        arr = map(int, (a["x"], a["y"], a["width"], a["height"]))   # convert to int
        return Geometry(*list(arr))

    def parsePlotcomBlock(self, buf, blocks):
        block = self.getNamedBlock("plotcom", blocks)
        if block is not None:
            self.parseColorAssignments(
                self.locateAssignments(
                    buf[block.start+1:block.end]
                    )
                )
            aa = self.locateAssignments(buf[block.start+1:block.end])
            for symbol in "clr bclr".split():
                if symbol in aa:
                    del aa[symbol]
            for k, v in aa.items():
                if k == "title":
                    self.title = v
                else:
                    self.contents[k] = v
            if "plotcom" in self.contents:
                del self.contents["plotcom"]


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

    def parseAdlBuffer(self, buf):              # lgtm [py/similar-function]
        logger.debug("\n"*2)
        logger.debug(self.given_filename)
        blocks = self.locateBlocks(buf)
        for block in blocks:
            logger.debug(str(block))

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
        blocks = [
            block
            for block in blocks
            if block.symbol in symbols.adl_widgets
            ]
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
        # assignments = self.locateAssignments(buf)   # ignore ncolors=
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

    def parseAdlBuffer(self, buf):              # lgtm [py/similar-function]
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)  # lgtm [py/unused-local-variable]
        if self.debug:
            _debug = self.debug  # lgtm [py/unused-local-variable]


class MedmArcWidget(MedmGenericWidget): pass
class MedmBarWidget(MedmGenericWidget): pass
class MedmByteWidget(MedmGenericWidget): pass


class MedmCartesianPlotWidget(MedmGenericWidget):

    def __init__(self, line, main, symbol):
        MedmGenericWidget.__init__(self, line, main, symbol)

    def parseAdlBuffer(self, buf):          # lgtm [py/similar-function]
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        self.parsePlotcomBlock(buf, blocks)

        for symbol in ("x_axis", "y1_axis", "y2_axis"):
            block = self.getNamedBlock(symbol, blocks)
            if block is not None:
                aa = self.locateAssignments(buf[block.start+1:block.end])
                self.contents[symbol] = aa

        traces = {}
        for block in blocks:
            if block.symbol.startswith("trace["):
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
        self.contents["traces"] = [traces[k] for k in sorted(traces.keys(), key=sorter)]


class MedmChoiceButtonWidget(MedmGenericWidget): pass


class MedmCompositeWidget(MedmBaseWidget):
    """contains other widgets or an entire .adl screen"""

    def __init__(self, line, main, symbol):
        MedmBaseWidget.__init__(self)
        self.line_offset = line
        self.main = main
        self.symbol = symbol        # "composite"
        self.widgets = []

    def parseAdlBuffer(self, buf):              # lgtm [py/similar-function]
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        block = self.getNamedBlock("children", blocks)
        if block is not None:
            # aa = self.locateAssignments(buf[block.start+1:block.end])
            bb = self.locateBlocks(buf[block.start+1:block.end])
            self.parseChildren(self.main, bb, buf[block.start+1:block.end])


class MedmEmbeddedDisplayWidget(MedmGenericWidget):
    debug = True # TODO: need example in .adl file!

    def __init__(self, line, main, symbol):
        # MedmGenericWidget.__init__(self, line, main, symbol)
        emsg = """Need this example!
            Support for MEDM's 'embedded display' widget not implemented yet.

            file: %s
            line: %d

            Please submit this file to the GitHub issue tracker
            (https://github.com/BCDA-APS/adl2pydm/issues/new)
            or email it to the author: <jemian@anl.gov>.

            see: https://github.com/BCDA-APS/adl2pydm/issues/13#issuecomment-546609321
        """ % (main.given_filename, line)
        raise NotImplementedError(emsg)

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

    def parseAdlBuffer(self, buf):          # lgtm [py/similar-function]
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

    def parseAdlBuffer(self, buf):          # lgtm [py/similar-function]
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

    def parseAdlBuffer(self, buf):          # lgtm [py/similar-function]
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)

        pens = {}
        for block in blocks:
            if block.symbol.startswith("pen["):
                del self.contents[block.symbol]
                aa = self.locateAssignments(buf[block.start+1:block.end])
                clr = aa.get("clr")
                if clr is not None:
                    del aa["clr"]
                    aa["color"] = self.main.color_table[int(clr)]
                row = block.symbol.replace("[", " ").replace("]", "").split()[-1]
                pens[row] = aa
            elif block.symbol == "plotcom":
                self.parsePlotcomBlock(buf, blocks)
            # elif block.symbol == "symbol":
            #     raise ValueError(block.symbol + " not handled yet")
            else:
                raise ValueError(block.symbol + " not expected here")

        def sorter(value):
            return int(value)
        self.contents["pens"] = [pens[k] for k in sorted(pens.keys(), key=sorter)]


class MedmTextWidget(MedmGenericWidget):

    def parseAdlBuffer(self, buf):              # lgtm [py/similar-function]
        assignments, blocks = MedmBaseWidget.parseAdlBuffer(self, buf)
        if "textix" in assignments:
            self.title = assignments["textix"]
            del self.contents["textix"], assignments["textix"]


class MedmTextEntryWidget(MedmGenericWidget): pass
class MedmTextUpdateWidget(MedmGenericWidget): pass
class MedmValuatorWidget(MedmGenericWidget): pass
class MedmWheelSwitchWidget(MedmGenericWidget): pass
