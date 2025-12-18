# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

processes_path = os.path.normpath(os.path.dirname(current_path) + '/processes')
TOOLS_PATH = "inspectia_tools"
processes_providers = []
processes_providers.append(TOOLS_PATH)


