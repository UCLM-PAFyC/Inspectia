# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))

from pyLibGisApi.defs import defs_server_api

PG_LAYERS_MANAGEMENT_DIALOG_TITLE = 'PostGIS Layers Management'
STYLE_LABEL = 'Style'
field_labels = []
layer_pg_field_label = {}
field_labels.append('Name')
layer_pg_field_label['Name'] = defs_server_api.LAYER_TAG_TABLE_NAME
field_labels.append('Title')
layer_pg_field_label['Title'] = defs_server_api.LAYER_TAG_TITLE
field_labels.append('Style')
layer_pg_field_label['Style'] = defs_server_api.LAYER_TAG_DEFAULT_STYLE

# LAYER_TAG_TABLE_NAME = 'name'
# LAYER_TAG_ID = 'layer_id'
# LAYER_TAG_TITLE = 'title'
# LAYER_TAG_DEFAULT_STYLE = 'default_style'
# LAYER_TAG_STYLES = 'styles'

