# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

IMAGES_PATH = "images"
LOGO_ICON_FILE = "logo.ico"
QDATE_TO_STRING_FORMAT = "yyyy:MM:dd"
TIME_STRING_FORMAT = "%H:%M:%S.%f"
DATE_STRING_FORMAT = "yyyy:MM:dd"
DATE_TIME_STRING_FORMAT = "%Y%m%d %H:%M:%S"
QDATETIME_TO_STRING_FORMAT_FOR_FILE_NAME = "yyyyMMdd_hhmmss"
TEMPLATES_PATH = "templates"
SETTINGS_FILE = "settings.ini"
NO_COMBO_SELECT = " ... "
MAIN_WIDGET_TITLE = "Inspectia"
GIS_SERVER_API_URL_DEFAULT = "https://inspectiawebgis.tidop.es"
# GIS_SERVER_API_EMAIL_DEFAULT = "user02@inspectia.es"
# GIS_SERVER_API_PASSWORD_DEFAULT = "user02@inspectia.es"
GIS_SERVER_DATA_MODEL_NAME = "inspectia-1-0"





