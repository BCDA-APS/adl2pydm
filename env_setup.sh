#!/bin/bash

#   . env_setup.sh

conda activate pydm
export PYQTDESIGNERPATH=${HOME}/Documents/eclipse/adl2pydm/pyqtdesignerpath:

# the  PYQTDESIGNERPATH directory contains this file:  pydm_designer_plugin.py
# and that file contains this one line:
#     from pydm.widgets.qtplugins import *

