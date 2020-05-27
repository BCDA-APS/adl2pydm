
"""
write the screen in the new XML protocol

Only rely on packages in the standard Python distribution. (rules out lxml)
"""

from collections import namedtuple
import json
import logging
import os
from xml.dom import minidom
from xml.etree import ElementTree

from . import symbols
from .adl_parser import Color, Geometry
from .calc2rules import convertCalcToRuleExpression


QT_STYLESHEET_FILE = "stylesheet.qss"
# the stylesheet should be in one of the directories in PYDM_DISPLAYS_PATH
ENV_PYDM_DISPLAYS_PATH = "PYDM_DISPLAYS_PATH"
SCREEN_FILE_EXTENSION = ".ui"
DEFAULT_NUMBER_OF_POINTS = 1200

logger = logging.getLogger(__name__)


def jsonDecode(src):
    "reads rules json text from .ui file"
    return json.loads(src)


def jsonEncode(rules):
    "writes rules as json text for .ui file"
    return json.dumps(rules)


def convertMacros(macros):
    """
    convert $(P)$(M) to ${P}${M}
    """
    return macros.replace("(", "{").replace(")", "}")


def replaceExtension(filename):
    """
    convert filename.adl to filename.ui
    """
    return os.path.splitext(filename)[0] + SCREEN_FILE_EXTENSION


def convertDynamicAttribute_to_Rules(attr):
    """
    interpret MEDM's "dynamic attribute" into PyDM's "rules"

    note difference in macro expression:

    ====  ======
    tool  macro
    ====  ======
    MEDM  `$(P)`
    PyDM  `${P}`
    ====  ======
    """
    rule = dict(name="visibility", property="Visible")
    channels = {}
    for nm, ref in dict(chan="A", chanB="B", chanC="C", chanD="D").items():
        if nm in attr:
            pv = convertMacros(attr[nm])
            channels[ref] = dict(channel=pv, trigger=len(pv)>0)

    calc = attr.get("calc")
    if calc is not None and len(calc) > 0:
        logger.info(f"CALC: {calc}")

    if len(channels) > 0:
        visibility_calc = {
            "if zero": " == 0",
            "if not zero": " != 0",
            "calc": calc
        }[attr.get("vis", "if not zero")]
        rule["channels"] = list(channels.values())
        if calc is None:
            calc = "a" + visibility_calc

    rule["expression"] = convertCalcToRuleExpression(calc)

    return [rule]


class Widget2Pydm(object):
    """
    convert screen to PyDM structure and write the '.ui' file

    NOTES

    describes the PyDM connection to Qt

    example:

        "cls",       "PyDMLineEdit"
        "extends",   "QLineEdit"
        "header",    "pydm.widgets.line_edit"

    """

    def __init__(self):
        self.custom_widgets = []
        self.unique_widget_names = {}
        self.pydm_widget_handlers = {
            "arc" : self.write_block_arc,
            "bar" : self.write_block_bar,
            "byte" : self.write_block_byte_indicator,
            "cartesian plot" : self.write_block_cartesian_plot,
            "choice button" : self.write_block_choice_button,
            "composite" : self.write_block_composite,
            "embedded display" : self.write_block_embedded_display,
            "image" : self.write_block_image,
            "indicator" : self.write_block_indicator,
            "menu" : self.write_block_menu,
            "message button" : self.write_block_message_button,
            "meter" : self.write_block_meter,
            "oval" : self.write_block_oval,
            "polygon" : self.write_block_polygon,
            "polyline" : self.write_block_polyline,
            "rectangle" : self.write_block_rectangle,
            "related display" : self.write_block_related_display,
            "shell command" : self.write_block_shell_command,
            "strip chart" : self.write_block_strip_chart,
            "text" : self.write_block_text,
            "text entry" : self.write_block_text_entry,
            "text update" : self.write_block_text_update,
            "valuator" : self.write_block_valuator,
            "wheel switch" : self.write_block_wheel_switch,
            }

    def get_unique_widget_name(self, suggestion):
        """
        return a widget name that is not already in use

        Qt requires that all widgets have a unique name.
        This algorithm keeps track of all widget names in use
        (basedon the suggested name) and, if the suggested name
        exists, generates a new name with an index number suffixed.
        """
        unique = suggestion

        if unique in self.unique_widget_names:
            knowns = self.unique_widget_names[suggestion]
            unique = "%s_%d" % (suggestion, len(knowns))
            if unique in self.unique_widget_names:
                msg = "trouble getting a unique name from " + suggestion
                msg += "\n  complicated:\n%s" % str(unique_widget_names)
                raise ValueError(msg)
        else:
            unique = suggestion
            self.unique_widget_names[suggestion] = []

        # add this one to the list
        self.unique_widget_names[suggestion].append(unique)

        return unique

    def get_channel(self, contents):
        """return the PV channel described in the MEDM widget"""
        pv = None
        for k in ("chan", "rdbk", "ctrl"):
            if k in contents:
                pv = contents[k]
        if pv is not None:
            pv = convertMacros(pv)
        return pv

    def processDynamicAttributeAsRules(self, widget, block):
        attr = block.contents.get("dynamic attribute", {})
        if len(attr) > 0:
            # see: http://slaclab.github.io/pydm/widgets/widget_rules/index.html
            rules = convertDynamicAttribute_to_Rules(attr)
            json_rules = jsonEncode(rules)
            self.writer.writeProperty(widget, "rules", json_rules, stdset="0")

    def write_basic_attribute(self, qw, block):
        attr = block.contents.get("basic attribute")
        if attr is None:
            return
        propty = self.writer.writeOpenProperty(qw, "brush", stdset="0")
        fill = dict(
            solid = "SolidPattern",
            outline = "NoBrush")[attr.get("fill", "solid")]
        brush = self.writer.writeOpenTag(propty, "brush", brushstyle=fill)
        self.write_color_element(brush, block.color, alpha="255")

        if qw.attrib["class"] not in ("PyDMLabel",):
            propty = self.writer.writeOpenProperty(qw, "penStyle", stdset="0")
            pen = dict(
                solid = "Qt::SolidLine",
                dash = "Qt::DashLine"
            )[attr.get("style", "solid")]
            self.writer.writeTaggedString(propty, "enum", pen)

            propty = self.writer.writeOpenProperty(qw, "penColor", stdset="0")
            self.write_color_element(propty, block.color)

            propty = self.writer.writeOpenProperty(qw, "penWidth", stdset="0")
            width = attr.get("width", 0)
            if fill == "NoBrush":
                width = max(1, float(width))   # make sure the outline is seen
            self.writer.writeTaggedString(propty, "double", str(width))

            propty = self.writer.writeOpenProperty(qw, "penCapStyle", stdset="0")
            self.writer.writeTaggedString(propty, "enum", "Qt::FlatCap")

            block.color = None

    def write_block(self, parent, block):
        nm = self.get_unique_widget_name(block.symbol.replace(" ", "_"))

        if (block.symbol == "composite"
                and len(block.widgets) == 0
                and "composite file" in block.contents):
            block.symbol = "embedded display"

        widget_info = symbols.adl_widgets.get(block.symbol)
        if widget_info is not None:
            cls = widget_info["pydm_widget"]
            if cls not in self.custom_widgets:
                self.custom_widgets.append(cls)

        handler = self.pydm_widget_handlers.get(
            block.symbol,
            self.write_block_default)
        cls = widget_info["pydm_widget"]
        # if block.symbol.find("chart") >= 0:
        #     _z = 2
        # TODO: PyDMDrawingMMM (Line, Polygon, Oval, ...) need more decisions here
        qw = self.writer.writeOpenTag(parent, "widget", cls=cls, name=nm)
        self.write_geometry(qw, block.geometry)
        # self.write_stylesheet(qw, block)
        handler(parent, block, nm, qw)
        msg = "(#%d) %s -> %s: %s" % (block.line_offset, block.symbol, cls, nm)
        logger.debug(msg)

    def write_color_element(self, xml_element, color, **kwargs):
        if color is not None:
            item = self.writer.writeOpenTag(xml_element, "color", **kwargs)
            self.writer.writeTaggedString(item, "red", str(color.r))
            self.writer.writeTaggedString(item, "green", str(color.g))
            self.writer.writeTaggedString(item, "blue", str(color.b))

    def write_direction(self, qw, block):
        # up & left only used in Bar Monitor
        direction = block.contents.get("direction", "right")
        orientation = {
            "left": "Qt::Horizontal",
            "right": "Qt::Horizontal",
            "up": "Qt::Vertical",
            "down": "Qt::Vertical",
        }[direction]
        self.writer.writeProperty(qw, "orientation", orientation, stdset="0")
        if (
            qw.attrib["class"] in ("PyDMScaleIndicator",)
            and
            direction in ("down", "left")
        ):
            self.writePropertyBoolean(qw, "invertedAppearance", True, stdset="0")

    def write_dynamic_attribute(self, qw, block):
        attr = block.contents.get("dynamic attribute")
        if attr is None:
            return
        self.processDynamicAttributeAsRules(qw, block)

    def write_font_size(self, qw, block, **kwargs):
        """
        constrain font size within geometry (height)
        """
        smallest = 4
        largest = 10
        margin = 3
        pointsize = int(max(smallest, min(largest, block.geometry.height - 2*margin)))

        propty = self.writer.writeOpenProperty(qw, "font", stdset="0")
        font = self.writer.writeOpenTag(propty, "font")
        self.writer.writeTaggedString(font, "pointsize", str(pointsize))

    def write_ui(self, screen, output_path):
        """main entry point to write the .ui file"""
        window_class = "QWidget"
        # window_class = "QMainWindow"
        title = screen.title or os.path.split(os.path.splitext(screen.given_filename)[0])[-1]
        ui_filename = os.path.join(output_path, title + SCREEN_FILE_EXTENSION)
        self.writer = PYDM_Writer(None)

        root = self.writer.openFile(ui_filename)
        logging.info("writing screen file: " + ui_filename)
        self.writer.writeTaggedString(root, "class", "Dialog")
        form = self.writer.writeOpenTag(root, "widget", cls=window_class, name="screen")

        self.write_geometry(form, screen.geometry)
        self.write_stylesheet(form, screen)

        propty = self.writer.writeOpenProperty(form, "windowTitle")
        self.writer.writeTaggedString(propty, value=title)

        for i, widget in enumerate(screen.widgets):
            # handle "widget" if it is a known screen component
            logger.debug(
                f"WIDGET {screen.given_filename}"
                f" {widget.line_offset}"
                f" {i+1}/{len(screen.widgets)}"
                f" {widget.symbol}"
            )
            self.write_block(form, widget)

        # TODO: self.write widget <zorder/> elements here (#7)

        self.write_customwidgets(root)

        # TODO: write .ui file <resources/> elements here (#9)
        # TODO: write .ui file <connections/> elements here (#10)

        self.writer.closeFile()

    def writePropertyBoolean(self, widget, tag, value, **kwargs):
        self.writer.writeProperty(widget, tag, str(value).lower(), tag="bool", **kwargs)

    def writePropertyStringlist(self, widget, title, strings, **kwargs):
        prop = self.writer.writeOpenProperty(widget, title, **kwargs)
        stringlist = self.writer.writeOpenTag(prop, "stringlist")
        for s in strings:
            self.writeStringText(stringlist, text=s.strip())

    def writePropertyTextAlignment(self, widget, attr):
        align =  {
            "horiz. left": "Qt::AlignLeading|Qt::AlignLeft|Qt::AlignVCenter",
            "horiz. centered" : "Qt::AlignCenter",
            "horiz. right" : "Qt::AlignRight|Qt::AlignTrailing|Qt::AlignVCenter",
            "justify" : "Qt::AlignJustify|Qt::AlignVCenter",
        }[attr.get("align", "horiz. left")]
        self.writer.writeProperty(widget, "alignment", align, tag="set")

    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

    def write_block_default(self, parent, block, nm, qw):
        self.write_tooltip(qw, "TBA widget: " + nm)
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)

    def write_block_arc(self, parent, block, nm, qw):
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)

        beginAngle = block.contents.get("beginAngle", 0)
        pathAngle = block.contents.get("pathAngle", 0)

        if beginAngle != 0:
            self.writer.writeProperty(
                qw,
                "startAngle",
                str(beginAngle),
                tag="double",
                stdset="0")
        if pathAngle != 0:
            self.writer.writeProperty(
                qw,
                "spanAngle",
                str(-pathAngle),
                tag="double",
                stdset="0")

    def write_block_bar(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["monitor"])
        self.write_channel(qw, pv)
        self.write_tooltip(qw, pv)
        self.write_direction(qw, block)
        self.write_limits(qw, block)
        self.writePropertyBoolean(qw, "barIndicator", True, stdset="0")
        showValue = False
        showTicks = False
        showLimits = False
        if block.contents.get("label") in ("limits", "channel"):
            showValue = True
            showTicks = True
        if block.contents.get("label") in ("limits",):
            showLimits = True
        self.writePropertyBoolean(qw, "showValue", showValue, stdset="0")
        self.writePropertyBoolean(qw, "showTicks", showTicks, stdset="0")
        self.writePropertyBoolean(qw, "showLimits", showLimits, stdset="0")
        # TODO: originAtZero

        color = self.writer.writeOpenProperty(qw, "indicatorColor", stdset="0")
        self.write_color_element(color, block.color)
        color = self.writer.writeOpenProperty(qw, "backgroundColor", stdset="0")
        self.write_color_element(color, block.background_color)
        block.color = None
        block.background_color = None

    def write_block_byte_indicator(self, parent, block, nm, qw):
        try:
            ebit = int(block.contents.get("ebit", 0))
            sbit = int(block.contents.get("sbit", 0))
        except Exception as exc:
            logger.critical(f"sbit/ebit: {exc}")
        numBits = 1 + max(ebit, sbit) - min(ebit, sbit)
        if numBits < 1:
            wmsg = "number of bits = %d" % numBits
            logger.warning(wmsg)

        self.write_tooltip(qw, nm)
        pv = self.get_channel(block.contents["monitor"])
        self.write_channel(qw, pv)

        color = self.writer.writeOpenProperty(qw, "onColor", stdset="0")
        self.write_color_element(color, block.color)
        color = self.writer.writeOpenProperty(qw, "offColor", stdset="0")
        self.write_color_element(color, block.background_color)
        block.color = None
        block.background_color = None

        self.write_direction(qw, block)
        self.writePropertyBoolean(qw, "showLabels", False, stdset="0")
        self.writePropertyBoolean(qw, "bigEndian", sbit < ebit, stdset="0")
        self.writer.writeProperty(qw, "numBits", numBits, tag="number", stdset="0")

    def write_block_choice_button(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["control"])
        self.write_tooltip(qw, pv)
        self.write_channel(qw, pv)
        self.write_font_size(qw, block)

        # MEDM stacking: row | column | row column
        stacking_choices = {
            # seems backwards
            # but MEDM shows a row with stacking = column
            "row": "Qt::Vertical",
            "column": "Qt::Horizontal",
            }
        stacking = block.contents.get("stacking", "row")
        if stacking not in stacking_choices:
            logger.warning(f"stacking '{stacking}' not supported, using 'row'")
            stacking = "row"
        orientation = stacking_choices[stacking]
        self.writer.writeProperty(qw, "orientation", orientation, stdset="0")
        for k in """
                horizontalSpacing   verticalSpacing
                margin_top          margin_bottom
                margin_left         margin_right
                """.split():
            self.writer.writeProperty(qw, k, 0, tag="number", stdset="0")

        self.write_stylesheet(
            qw,
            block,
            margin = "0px",
            padding = "0px",
            spacing = "0px",
            # PyDMEnumButton: add color styles for the buttons
            extra_classes = "QPushButton QRadioButton".split(),
            )

    def writePropertyContentsLabel(self, qw, block, label, tag=None):
        tag = tag or label
        text = block.contents.get(label)
        if text is not None:
            self.writer.writeProperty(qw, tag, text)

    def write_block_cartesian_plot(self, parent, block, nm, qw):
        """
        Could be either PyDMWaveformPlot or PyDMScatterPlot
        """
        logger.debug("line %d in file: %s" % (block.line_offset, block.main.given_filename))
        # logger.debug("contents:\n" + json.dumps(block.contents, indent=2))
        self.write_tooltip(qw, nm)
        self.writer.writeProperty(qw, "title", block.title, stdset="0")

        count = block.contents.get("count", DEFAULT_NUMBER_OF_POINTS)
        try:
            count = int(count)
        except ValueError:
            logger.warning(
                "number of plot points must be an integer, "
                f"using {DEFAULT_NUMBER_OF_POINTS} points "
                f"instead of '{count}'"
            )
            count = DEFAULT_NUMBER_OF_POINTS

        xlabel = block.contents.get("xlabel")
        ylabel = block.contents.get("ylabel")

        curves = []
        for i, trace in enumerate(block.contents.get("traces", [])):
            # ignore trace["yaxis"], in PyDM, all traces share same Y axis
            # collect any available information
            curve = dict(
                name = f"curve {i+1}",
                # if x_channel is missing, y_channel is plotted aginst index
                x_channel = trace.get("xdata"),
                y_channel = trace.get("ydata"),
                color = "#{:02x}{:02x}{:02x}".format(*trace["color"]),
                lineStyle = 1,          # NoLine Solid Dash Dot DashDot DashDotDot
                lineWidth = trace.get("lineWidth", 1),
                symbol = trace.get("symbol"),
                symbolSize = trace.get("symbolSize", 10),
                redraw_mode = 2,    # "X or Y updates", "X updates", "Y updates", "Both update"
                block_size = count,
            )
            curve = {   # remove undefined values from the dictionary
                k: curve[k]
                for k in list(curve.keys())
                if curve[k] is not None
                }
            curve["x_channel"] = curve.get("x_channel", None)
            for k in "x_channel y_channel".split():
                if k in curve and curve[k] is not None:
                    # add the "ca://" prefix
                    curve[k] = f"ca://{convertMacros(curve[k])}"
            if "y_channel" in curve:
                curves.append(jsonEncode(curve))

        # write the PyDMScatterPlot contents
        if xlabel is not None and len(xlabel) > 0:
            self.writePropertyStringlist(qw, "xLabels", [convertMacros(xlabel),])
        if ylabel is not None and len(ylabel) > 0:
            self.writePropertyStringlist(qw, "yLabels", [convertMacros(ylabel),])
        self.writePropertyStringlist(qw, "curves", curves, stdset="0")

        # TODO: add this code back?
        # scales = dict(autoRangeX=True, autoRangeY=True)
        # for axis in "x_axis y1_axis y2_axis".split():
        #     rangeStyle = block.contents.get(axis, {}).get("rangeStyle")
        #     option = rangeStyle == "auto-scale"
        #     scales["autoRange"+axis[0].upper()] = option
        # for k, v in scales.items():
        #     self.writePropertyBoolean(qw, k, v, stdset="0")

        color = self.writer.writeOpenProperty(qw, "axisColor", stdset="0")
        self.write_color_element(color, block.color)
        color = self.writer.writeOpenProperty(qw, "backgroundColor", stdset="0")
        self.write_color_element(color, block.background_color)
        block.color = None
        block.background_color = None


    def write_block_composite(self, parent, block, nm, qw):
        # self.write_tooltip(qw, nm)
        self.write_dynamic_attribute(qw, block)
        x0 = block.geometry.x
        y0 = block.geometry.y
        for widget in block.widgets:
            # in MEDM, composites use absolute positioning
            # in PyDM, composites use relative positioning
            # subtract x,y of the composite from each widget
            widget.geometry = Geometry(
                widget.geometry.x - x0,
                widget.geometry.y - y0,
                widget.geometry.width,
                widget.geometry.height,
            )
            self.write_block(qw, widget)

    def write_block_embedded_display(self, parent, block, nm, qw):
        self.write_tooltip(qw, nm)
        # has block.contents["composite file"] and block.contents["composite name"]
        # Note: composite file is a list delimited by ";"
        filelist = block.contents["composite file"].split(";")
        macros = None
        if len(filelist) != 1:
            if len(filelist) == 2:
                macros = convertMacros(filelist[1])
            elif len(filelist) < 1:
                emsg = "'composite file' list was empty"
                emsg += " (file: %s, line %d)" % (block.main.given_filename, block.line_offset)
                logger.error(emsg)
                return
            # else:
            #     emsg = "Rendering only first file from 'composite file'"
            #     emsg += "=%s" % block.contents["composite file"]
            #     emsg += " (file: %s, line %d)" % (block.main.given_filename, block.line_offset)
            #     logger.warning(emsg)
        filename = replaceExtension(filelist[0])
        self.writer.writeProperty(qw, "filename", filename, stdset="0")
        if macros is not None:
            macros = convertMacros(macros)
            self.writer.writeProperty(qw, "macros", convertMacros(macros), stdset="0")

    def write_block_image(self, parent, block, nm, qw):
        image_name = block.contents.get("image name")
        self.writer.writeProperty(qw, "filename", image_name, tag="string", stdset="0")
        self.write_dynamic_attribute(qw, block)
        self.write_tooltip(qw, nm)

    def write_block_indicator(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["monitor"])
        self.write_tooltip(qw, pv)
        self.write_channel(qw, pv)
        self.write_limits(qw, block)
        self.write_direction(qw, block)

        precision = block.contents.get("precision")        # TODO: needs an example from .adl
        if precision is not None:
            logger.warning("precision needs an example .adl file")

    def write_block_menu(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["control"])
        self.write_tooltip(qw, pv)
        self.write_channel(qw, pv)
        self.write_font_size(qw, block)
        self.write_stylesheet(qw, block)

    def write_block_message_button(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["control"])
        self.writer.writeProperty(qw, "text", block.title, tag="string")
        self.write_font_size(qw, block)
        self.write_tooltip(qw, pv)
        self.write_channel(qw, pv)
        msg = block.contents.get("press_msg")
        if msg is not None:
            self.writer.writeProperty(qw, "pressValue", msg, stdset="0")
        self.write_stylesheet(qw, block)

    def write_block_meter(self, parent, block, nm, qw):
        # handle same as indicator since PyDM does not have a meter widget
        self.write_block_indicator(parent, block, nm, qw)

    def write_block_oval(self, parent, block, nm, qw):
        ba = block.contents["basic attribute"]
        da = block.contents.get("dynamic attribute", {})
        pv = self.get_channel(da)
        if pv is not None:
            self.write_channel(qw, pv)
            self.write_tooltip(qw, nm)
            self.write_dynamic_attribute(qw, block)

        brushstyles = {
            "solid" : "SolidPattern",
            "outline" : "NoBrush",
        }
        adl_fill = ba.get("fill", "solid")
        brushstyle = brushstyles.get(adl_fill, "solid")
        brushProp = self.writer.writeOpenProperty(qw, "brush", stdset="0")
        brush = self.writer.writeOpenTag(
            brushProp, "brush", brushstyle=brushstyle)
        self.write_color_element(brush, block.color, alpha="255")

        penStyles = {
            "solid" : "Qt::SolidLine",
            "dash" : "Qt::DashLine",
        }
        adl_style = ba.get("style", "solid")
        penStyle = penStyles.get(adl_style, "solid")
        self.writer.writeProperty(
            qw, "penStyle", penStyle, tag="enum", stdset="0")

        penColor = self.writer.writeOpenProperty(qw, "penColor", stdset="0")
        self.write_color_element(penColor, block.color)

        block.color = None
        block.background_color = None

        penWidth = float(ba.get("width", 0))
        if penWidth > 0:
            self.writer.writeProperty(
                qw, "penWidth", penWidth, tag="double", stdset="0")

    def write_block_polygon(self, parent, block, nm, qw):
        self.write_tooltip(qw, "PyDMDrawingIrregularPolygon\nwidget not yet ready")
        # TODO:
        # these lines from polyline support
        self.write_tooltip(qw, nm)
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)
        # FIXME: needs to support fill = "solid"
        ba = block.contents.get("basic attribute", {})
        try:
            penWidth = int(ba.get("width", 1))
        except Exception as exc:
            logger.critical(f"penWidth: {exc}")
            penWidth = 1

        pt_list = []
        for pt in block.points:
            # translate global to local
            x = pt.x - block.geometry.x - penWidth
            y = pt.y - block.geometry.y - penWidth
            pt_list.append("%d, %d" % (x, y))
        self.writePropertyStringlist(qw, "points", pt_list, stdset="0")

    def write_block_polyline(self, parent, block, nm, qw):
        self.write_tooltip(qw, nm)
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)
        ba = block.contents.get("basic attribute", {})
        try:
            penWidth = int(ba.get("width", 1))
        except Exception as exc:
            logger.critical(f"penWidth: {exc}")
            penWidth = 1

        da = block.contents.get("dynamic attribute", {})
        pv = self.get_channel(da)
        if pv is not None:
            self.write_channel(qw, pv)

        pt_list = []
        for pt in block.points:
            # translate global to local
            x = pt.x - block.geometry.x - penWidth
            y = pt.y - block.geometry.y - penWidth
            pt_list.append("%d, %d" % (x, y))
        self.writePropertyStringlist(qw, "points", pt_list, stdset="0")

    def write_block_rectangle(self, parent, block, nm, qw):
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)
        self.write_tooltip(qw, nm)

    def write_block_related_display(self, parent, block, nm, qw):
        text = block.title

        showIcon = True
        if text is not None:
            showIcon = not text.startswith("-")
            text = convertMacros(text.lstrip("-"))
            self.write_tooltip(qw, text)
            self.writer.writeProperty(qw, "text", text, tag="string")
        logger.debug(f"relatedDisplay showIcon={showIcon}  text='{text}''")
        self.writePropertyBoolean(qw, "showIcon", showIcon, stdset="0")

        self.write_font_size(qw, block)
        self.write_stylesheet(qw, block)
        replaceDisplay = True
        if hasattr(block, "displays"):
            displays = {
                "titles" : [convertMacros(d.get("label", "")) for d in block.displays],
                "filenames" : [replaceExtension(d.get("name", "")) for d in block.displays],
                "macros" : [convertMacros(d.get("args", "")) for d in block.displays],
            }
            for tag, items in displays.items():
                self.writePropertyStringlist(qw, tag, items, stdset="0")
            policies = [
                d.get("policy", "") == "replace display"
                for d in block.displays]
            replaceDisplay = True not in policies

        self.writePropertyBoolean(qw, "openInNewWindow", replaceDisplay, stdset="0")
        """
        <property name="openInNewWindow" stdset="0">
            <bool>true</bool>
        </property>
        inside the widget
        """

    def write_block_shell_command(self, parent, block, nm, qw):
        self.write_tooltip(qw, nm)

        # first: gather shell command contents
        title_list = []
        command_list = []
        for spec in block.commands:
            title_list.append(spec.get("label", ""))
            command_list.append("%s %s" % (spec["name"], spec.get("args", "")))

        if len(command_list) > 0:
            # second: assemble XML structures
            self.writePropertyStringlist(qw, "titles", title_list, stdset="0")
            self.writePropertyStringlist(qw, "commands", command_list, stdset="0")

        title = block.title or ""
        if len(title) > 0:
            logger.debug(f"title={title}")
            if title.startswith("-"):     # MEDM rule, use "-" prefix to hide the icon
                self.writePropertyBoolean(qw, "showIcon", False, stdset="0")
                title = title[1:]
            self.writer.writeProperty(qw, "text", title)

        # impose MEDM behavior
        self.writePropertyBoolean(qw, "allowMultipleExecutions", True, stdset="0")

    def write_block_strip_chart(self, parent, block, nm, qw):
        self.write_tooltip(qw, nm)
        self.writer.writeProperty(qw, "title", block.title, stdset="0")
        period = block.contents.get("period")
        if period is not None:
            # The period is the time between updates (s)
            self.writer.writeProperty(
                qw, "updateInterval",
                str(period),
                tag="double",
                stdset="0")

        if len(block.contents["pens"]) > 0:
            text = block.contents.get("xlabel")
            if text is not None:
                self.writer.writeProperty(qw, "xLabels", text)
            text = block.contents.get("ylabel")
            if text is not None:
                self.writer.writeProperty(qw, "yLabels", text)

            curves = []
            for v in block.contents["pens"]:
                c = v["color"]
                trace = dict(
                    color = "#%02x%02x%02x" % (c.r, c.g, c.b),
                    # MEDM only supports Solid line with color, width=1
                    lineStyle = 1,          # NoLine Solid Dash Dot DashDot DashDotDot
                    lineWidth = 1,
                )
                if "chan" in v:
                    trace["channel"] = "ca://" + convertMacros(v["chan"])
                    trace["name"] = v["chan"]

                curves.append(jsonEncode(trace))

            self.writePropertyStringlist(qw, "curves", curves, stdset="0")

    def write_block_text(self, parent, block, nm, qw):
        text = block.title
        if block.title is not None:
            text = convertMacros(block.title)
        self.writer.writeProperty(qw, "text", text, tag="string")
        self.write_font_size(qw, block)
        self.write_basic_attribute(qw, block)
        self.write_dynamic_attribute(qw, block)
        self.write_tooltip(qw, nm)
        self.writePropertyTextAlignment(qw, block.contents)
        self.write_stylesheet(qw, block)

    def write_block_text_entry(self, parent, block, nm, qw):
        # must wrap in a QFrame to get sunken border look
        #   and a layout to fill the space
        # line width = 2    # makes the text entry smaller
        # frame shape = Panel
        # frame shadow = Sunken
        pv = self.get_channel(block.contents["control"])
        if pv is not None:
            self.write_channel(qw, pv)
            self.write_tooltip(qw, pv)
            self.write_display_format(qw, pv, block)

        self.write_font_size(qw, block)
        self.write_stylesheet(
            qw,
            block,
            border="1px solid black",   # alternative to QFrame
            margin="0px",
            padding="0px",
            spacing="0px",
            )

    def write_block_text_update(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["monitor"])
        if pv is not None:
            self.write_tooltip(qw, "PV: " + pv)
            self.write_channel(qw, pv)
            self.write_display_format(qw, pv, block)

        self.write_font_size(qw, block)
        self.writePropertyTextAlignment(qw, block.contents)
        flags = "Qt::TextSelectableByKeyboard|Qt::TextSelectableByMouse"
        self.writer.writeProperty(qw, "textInteractionFlags", flags, tag="set")
        self.write_stylesheet(qw, block)

    def write_block_valuator(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["control"])
        self.write_channel(qw, pv)
        self.write_tooltip(qw, pv)
        self.write_direction(qw, block)
        self.write_limits(qw, block)

        # TODO:
        # TODO: https://github.com/BCDA-APS/adl2pydm/issues/50
        # self.assertEqualPropertyBool(w, "showValueLabel", False)
        # self.assertEqualPropertyBool(w, "showLimitLabels", False)

        # TODO: https://github.com/BCDA-APS/adl2pydm/issues/37
        precision = block.contents.get("dPrecision")
        if precision is not None:
            self.writer.writeProperty(
                qw, "precision", str(precision), tag="number")

    def write_block_wheel_switch(self, parent, block, nm, qw):
        pv = self.get_channel(block.contents["control"])
        self.write_channel(qw, pv)
        self.write_tooltip(qw, pv)
        self.write_limits(qw, block)

        format = block.contents.get("format")
        if format is not None:
            wmsg = "wheel switch format is unsupported now: " + format
            logger.warning(wmsg)
            # TODO: format -
            # maybe not be supported in Qt QDoubleSpinBox
            # https://doc.qt.io/qt-5/qdoublespinbox.html#details
            # If the Format is not specified,
            #   then the WheelSwitch calculates it
            #   based on the low and high limits and
            #   the precision.
            # https://epics.anl.gov/EpicsDocumentation/ExtensionsManuals/MEDM/MEDM.html#Label

    # . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .

    def write_channel(self, parent, channel):
        logger.debug("PV channel: " + channel)
        propty = self.writer.writeOpenProperty(parent, "channel", stdset="0")
        # stdset=0 signals this attribute is from PyDM, not Qt widget
        self.writer.writeTaggedString(
            propty,
            value=f"ca://{convertMacros(channel)}",
            )

    def write_display_format(self, parent, pv, block):
        if (
            # https://epics.anl.gov/EpicsDocumentation/ExtensionsManuals/MEDM/MEDM.html#TextFormat
            # ? also "compact"
            block.contents.get("format") in ("string", )
            or
            # long string suffix found, render as string
            convertMacros(pv).endswith("$")
        ):
            logger.debug("Setting 'string' format.")
            self.writer.writeProperty(
                parent,
                "displayFormat",
                f"{parent.attrib['class']}::String",
                tag="enum",
                stdset="0")

    def write_stylesheet(self, parent, block, **kwargs):
        """
        write the style sheet, principally, the colors

        other style settings are provided in the kwargs dict
        """
        others = []
        if "extra_classes" in kwargs:
            others = kwargs.pop("extra_classes")

        parts = []
        fmt = "  %s: rgb(%d, %d, %d);"
        if block.color is not None:
            parts.append(fmt % ("color", *block.color))

        if block.background_color is not None:
            parts.append(fmt % ("background-color", *block.background_color))

        for k, v in kwargs.items():
            parts.append(f"  {k}: {v};")

        if len(parts) > 0:
            #
            settings = [f"{parent.attrib['class']}#{parent.attrib['name']}" + " {",]
            settings += parts
            settings.append("  }")
            for cls in others:
                # special case
                # copy color styles to interior widgets
                settings.append(f"{cls}" + " {")
                settings += [
                    v
                    for v in parts
                    if v.strip().split()[0] in (
                        "color:",
                        "background-color:"
                    )
                ]
                settings.append("  }")
            style = "\n".join(settings)

            propty = self.writer.writeOpenProperty(parent, "styleSheet")
            ss = self.writer.writeOpenTag(propty, "string", notr="true")
            ss.text = style

    def write_customwidgets(self, parent):
        cw_set = self.writer.writeOpenTag(parent, "customwidgets")

        # some custom widgets extend other custom widgets
        # include any inheritances
        # example: PyDMDrawingPie extends PyDMDrawingArc
        while True:     # do..until
            additions = []
            for widget in self.custom_widgets:
                if widget == "PyDMDrawingPie":
                    logger.debug("breakpoint")
                item = symbols.pydm_widgets.get(widget)
                if item is not None:
                    klass = item.extends
                    if klass.startswith("PyDM") and klass not in additions+self.custom_widgets:
                        additions.append(klass)
            if len(additions) > 0:
                self.custom_widgets += additions
            else:
                break   #recurse until no new additions

        for widget in self.custom_widgets:
            item = symbols.pydm_widgets.get(widget)
            if item is not None:
                cw = self.writer.writeOpenTag(cw_set, "customwidget")
                self.writer.writeTaggedString(cw, "class", item.cls)
                self.writer.writeTaggedString(cw, "extends", item.extends)
                self.writer.writeTaggedString(cw, "header", item.header)

    def write_geometry(self, parent, geom):
        propty = self.writer.writeOpenProperty(parent, "geometry")
        rect = self.writer.writeOpenTag(propty, "rect")
        # if str(geom.x) == "-":
        #     _debug_ = True
        self.writer.writeTaggedString(rect, "x", str(geom.x))
        self.writer.writeTaggedString(rect, "y", str(geom.y))
        self.writer.writeTaggedString(rect, "width", str(geom.width))
        self.writer.writeTaggedString(rect, "height", str(geom.height))

    def write_limits(self, qw, block):
        if (
            block.contents.get("hoprSrc") == "default"
            or
            block.contents.get("loprSrc") == "default"
        ):
            # TODO: precDefault gives info about the step size if precSrc == "default"
            precSrc = block.contents.get("precSrc")
            precDefault = block.contents.get("precDefault")

            label = block.contents.get("label")
            # https://epics.anl.gov/EpicsDocumentation/ExtensionsManuals/MEDM/MEDM.html#Label
            if label is None:
                show = dict(limits=True, values=False)
            elif label == "no decorations":
                # TODO: For the Bar Monitor, only the background and the bar show
                show = dict(limits=True, values=False)
            elif label == "outline":
                show = dict(limits=True, values=False)
            elif label == "limits":
                show = dict(limits=True, values=True)
            elif label == "channel":
                show = dict(limits=True, values=True)
            self.writePropertyBoolean(qw, "showLimitLabels", show["limits"], stdset="0")
            self.writePropertyBoolean(qw, "showValueLabel", show["values"], stdset="0")

            if qw.attrib["class"] == "PyDMScaleIndicator":
                self.writePropertyBoolean(qw, "limitsFromChannel", False, stdset="0")
                hiLimitName = "userUpperLimit"
                loLimitName = "userLowerLimit"
            elif qw.attrib["class"] == "PyDMSlider":
                hiLimitName = "userMaximum"
                loLimitName = "userMinimum"
            elif qw.attrib["class"] == "PyDMSpinbox":
                hiLimitName = "maximum"
                loLimitName = "minimum"
            else:
                raise NotImplementedError(
                    f"limits for {qw.attrib['class']} widget not handled"
                    )

            self.writePropertyBoolean(qw, "userDefinedLimits", True, stdset="0")
            self.writer.writeProperty(
                qw,
                hiLimitName,
                block.contents.get("hoprDefault", str(0.0)),
                tag="double",
                stdset="0")
            self.writer.writeProperty(
                qw,
                loLimitName,
                block.contents.get("loprDefault", str(0.0)),
                tag="double",
                stdset="0")

    def writeStringText(self, parent, tag="string", text=""):
        s = self.writer.writeOpenTag(parent, tag)
        s.text = text
        return s

    def write_tooltip(self, parent, tip):
        propty = self.writer.writeOpenProperty(parent, "toolTip")
        self.writer.writeTaggedString(propty, value=tip)


"""
control the stacking order of Qt widgets - important!

Sets the stacking order of sibling items.
By default the stacking order is 0.

* Items with a higher stacking value are drawn
    on top of siblings with a lower stacking order.
* Items with the same stacking value are drawn
    bottom up in the order they appear.
* Items with a negative stacking value are drawn
    under their parent's content.

PARAMS

order (int) :
    sorting order

vis (int) :
    is this widget visible?

text (str) :
    the text content

Example how the zorder is given in the .ui file:

    <zorder>caRectangle_0</zorder>
    <zorder>caRectangle_1</zorder>
    <zorder>caLabel_0</zorder>
    <zorder>caLabel_1</zorder>
    ...
"""
Qt_zOrder = namedtuple('Qt_zOrder', 'order vis text')


class PYDM_Writer(object):
    """
    write the screen description to a PyDM .ui file
    """

    def __init__(self, adlParser):
        self.adlParser = adlParser
        self.filename = None
        self.path = None
        self.file_suffix = SCREEN_FILE_EXTENSION
        self.stylesheet = None
        self.root = None
        self.outFile = None
        self.widget_stacking_info = []        # stacking order

    def openFile(self, outFile):
        """actually, begin to create the .ui file content IN MEMORY"""
        if os.environ.get(ENV_PYDM_DISPLAYS_PATH) is None:
            msg = "Environment variable %s is not defined." % "PYDM_DISPLAYS_PATH"
            logger.info(msg)

        sfile = findFile(QT_STYLESHEET_FILE)
        if sfile is None:
            msg = "file not found: " + QT_STYLESHEET_FILE
            logger.info(msg)
        else:
            with open(sfile, "r") as fp:
                self.stylesheet = fp.read()
                msg = "Using stylesheet file in .ui files: " + sfile
                msg += "\n  unset %d to not use any stylesheet" % ENV_PYDM_DISPLAYS_PATH
                logger.info(msg)

        # adl2ui opened outFile here AND started to write XML-like content
        # that is not necessary now
        if os.path.exists(outFile):
            msg = "output file already exists: " + outFile
            logger.info(msg)
        self.outFile = outFile

        # Qt .ui files are XML, use XMl tools to create the content
        # create the XML file root element
        self.root = ElementTree.Element("ui", attrib=dict(version="4.0"))
        # write the XML to the file in the close() method

        return self.root

    def closeFile(self):
        """finally, write .ui file (XML content)"""

        def sorter(widget):
            return widget.order

        # sort widgets by the order we had when parsing
        for widget in sorted(self.widget_stacking_info, key=sorter):
            z = ElementTree.SubElement(self.root, "zorder")
            # TODO: what about "vis" field?
            z.text = str(widget.text)

        # ElementTree needs help to pretty print
        # (easier in lxml but that's an additional package to add)
        text = ElementTree.tostring(self.root)
        xmlstr = minidom.parseString(text).toprettyxml(indent=" "*2)
        with open(self.outFile, "w") as f:
            f.write(xmlstr)

    def writeProperty(self, parent, name, value, tag="string", **kwargs):
        prop = self.writeOpenTag(parent, "property", name=name)
        self.writeTaggedString(prop, tag, value)
        for k, v in kwargs.items():
            prop.attrib[k] = v
        return prop

    def writeOpenProperty(self, parent, name, **kwargs):
        prop = self.writeOpenTag(parent, "property", name=name)
        for k, v in kwargs.items():
            prop.attrib[k] = v
        return prop

    def writeTaggedString(self, parent, tag="string", value=None):
        element = ElementTree.SubElement(parent, tag)
        if value is not None:
            element.text = str(value)
        return element

    # def writeCloseProperty(self): ...        # nothing to do

    def writeOpenTag(self, parent, tag, cls="", name="", **kwargs):
        if parent is None:
            msg = "writeOpenTag(): parent is None, cannot continue"
            raise ValueError(msg)
        element = ElementTree.SubElement(parent, tag)
        if len(cls) > 0:
            element.attrib["class"] = cls
        if len(name) > 0:
            element.attrib["name"] = name
        for k, v in kwargs.items():
            element.attrib[k] = v
        return element

    # def writeCloseTag(self, tag): ...        # nothing to do
    # def writeMessage(self, mess): ...        # nothing to do


def findFile(fname):
    """look for file in PYDM_DISPLAYS_PATH"""
    if fname is None or len(fname) == 0:
        return None

    if os.name =="nt":
        delimiter = ";"
    else:
        delimiter = ":"

    path = os.environ.get(ENV_PYDM_DISPLAYS_PATH)
    if path is None:
        paths = [os.getcwd()]      # safe choice that becomes redundant
    else:
        paths = path.split(delimiter)

    if os.path.exists(fname):
        # found it in current directory
        return fname

    for path in paths:
        path_fname = os.path.join(path, fname)
        if os.path.exists(path_fname):
            # found it in the DISPLAYS path
            return path_fname

    return None
