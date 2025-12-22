# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from defs import defs_paths
common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from pyLibGisApi.defs import defs_processes as gis_api_defs_processes

processes_path = os.path.normpath(os.path.dirname(current_path) + '/processes')
TOOLS_PATH = "tools"
processes_providers = []
processes_providers.append(TOOLS_PATH)

ignored_process_name_by_provider = {}
for provider in processes_providers:
    ignored_process_name_by_provider[provider] = []
for provider in gis_api_defs_processes.processes_providers:
    if not provider in ignored_process_name_by_provider:
        ignored_process_name_by_provider[provider] = []
# ignored_process_name_by_provider[photogrammetry_defs_processes.LIB_PATH].append("Get Image Footprints")

process_path_by_provider = {}
for provider in processes_providers:
    process_path_by_provider[provider] = []
    process_path_by_provider[provider].append(processes_path)
for provider in gis_api_defs_processes.processes_providers:
    if not provider in process_path_by_provider:
        process_path_by_provider[provider] = []
    process_path_by_provider[provider].append(gis_api_defs_processes.processes_path)


