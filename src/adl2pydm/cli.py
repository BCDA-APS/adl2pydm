#!/usr/bin/env python

"""
convert MEDM .adl screen file(s) to PyDM .ui format

Only rely on packages in this project or from the standard Python distribution.
"""

import argparse
# from collections import namedtuple
import logging
import os

from . import adl_parser
from . import output_handler


logger = None


def processFile(adl_filename, output_path=None):
    output_path = output_path or os.path.dirname(adl_filename)

    screen = adl_parser.MedmMainWidget(adl_filename)
    buf = screen.getAdlLines(adl_filename)
    screen.parseAdlBuffer(buf)

    writer = output_handler.Widget2Pydm()
    writer.write_ui(screen, output_path)


def get_user_parameters():
    import adl2pydm
    doc = __doc__.strip().splitlines()[0]
    doc += ' (%s)' % adl2pydm.__url__
    doc += ' v' + adl2pydm.__version__
    parser = argparse.ArgumentParser(
        prog=adl2pydm.__package__, description=doc)

    msg = "MEDM '.adl' file(s) to convert"
    parser.add_argument(
        'adlfiles',
        action='store',
        nargs=argparse.ONE_OR_MORE,
        help=msg,
        )

    msg =  "output directory"
    msg += ", default: same directory as input file"
    parser.add_argument(
        '-d',
        '--dir',
        action='store',
        dest='dir',
        help=msg,
        default=None)

    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version=adl2pydm.__version__)

    parser.add_argument(
        "-log",
        "--log",
        default="warning",
        help=(
            "Provide logging level. "
            "Example --log debug', default='warning'"),
        )

    parser.add_argument(
        "--use-scatterplot",
        action="store_true",
        default=False,
        help=(
            "Translate MEDM 'cartesian plot' widget as `PyDMScatterPlot` "
            "instead of `PyDMWaveformPlot`, default=False"),
        )

    return parser.parse_args()


def configure_logging(options):
    global logger
    levels = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warn': logging.WARNING,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG
    }
    level = levels.get(options.log.lower())
    if level is None:
        raise ValueError(
            f"log level given: {options.log}"
            f" -- must be one of: {' | '.join(levels.keys())}")
    logging.basicConfig(level=level)
    logger = logging.getLogger(__name__)


def main():
    options = get_user_parameters()
    configure_logging(options)

    if options.use_scatterplot:
        from .symbols import adl_widgets
        adl_widgets["cartesian plot"]["pydm_widget"] = "PyDMScatterPlot"

    for adlfile in options.adlfiles:
        try:
            processFile(adlfile, options.dir)
        except Exception as exc:
            logger.error(
                f"error processing {adlfile}:"
                f" {exc}"
            )


# if __name__ == "__main__":
#     main()
