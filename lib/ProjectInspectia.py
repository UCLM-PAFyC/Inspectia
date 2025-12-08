# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
import json
import xmltodict

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

from PyQt5.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

from Inspectia.defs import defs_paths
common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from pyLibProject.defs import defs_project_definition
from pyLibProject.lib.Project import Project
from pyLibProject.defs import defs_project
from pyLibGisApi.lib.PostGISServerAPI import PostGISServerConnection
from pyLibGisApi.defs import defs_server_api

class ProjectInspectia(Project):
    def __init__(self, qgis_iface, settings, crs_tools, pgs_connection):
        super().__init__(qgis_iface, settings, crs_tools)
        self.pgs_connection = pgs_connection
        self.db_project = None
        self.layer_name_prefix = None
        self.db_schema = ''

    def add_map_view(self,
                     map_view_id,
                     map_view_wkb_geometry):
        str_error = ''
        if map_view_id in self.map_views:
            str_error = ('Exists a previous location with name: {}'.format(map_view_id))
            return str_error
        if not defs_server_api.PROJECT_TAG_WFS_SERVICE in self.db_project:
            str_error = ('Not exists tag: {} in db_project'.format(defs_server_api.PROJECT_TAG_WFS_SERVICE))
            return str_error
        wfs_service = self.db_project[defs_server_api.PROJECT_TAG_WFS_SERVICE]
        wfs_url = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_URL]
        wfs_user = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_USER]
        wfs_password = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_PASSWORD]
        return super().add_map_view(map_view_id, map_view_wkb_geometry, wfs = [wfs_url, wfs_user, wfs_password])

    def create(self, parent_widget = None):
        str_error = ''
        definition_is_saved = False
        str_error = self.pgs_connection.get_projects()
        if str_error:
            str_error = ('Error getting projects:\n{}'.format(str_error))
            return str_error, definition_is_saved
        is_process_creation = True
        user_name = self.pgs_connection.user[defs_server_api.USERS_TAG_NAME]
        self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_AUTHOR] = user_name
        str_error, definition_is_saved = self.project_definition_gui(is_process_creation, parent_widget)
        if str_error:
            str_error = ('Project definition, error:\n{}'.format(str_error))
            return str_error, definition_is_saved
        # while not definition_is_saved:
        #     str_error, definition_is_saved = self.project_definition_gui(is_process_creation, parent_widget)
        #     if str_error:
        #         str_error = ('Project definition, error:\n{}'.format(str_error))
        #         return str_error
        if not definition_is_saved:
            return str_error, definition_is_saved
        project_name = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_NAME]
        str_error, db_project = self.pgs_connection.get_project_by_name(project_name)
        if str_error:
            str_error = ('Recovering created project: {}, error:\n{}'.format(project_name, str_error))
            return str_error, definition_is_saved
        project_id = db_project[defs_server_api.PROJECT_TAG_ID]
        db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)

        # create layers
        str_error = super().create_layers(db_schema = db_schema)
        if str_error:
            str_error = ('For created project: {}, error recovering SQLs to create parent layers:\n{}'
                         .format(project_name, str_error))
            return str_error, definition_is_saved
        sqls = self.sqls_to_process
        # # CREATE TABLE Lab1.
        # str_create_table_with_squema = ('CREATE TABLE {}.'.format(self.db_schema))
        # for i in range(len(sqls)):
        #     sql = sqls[i]
        #     sql = sql.replace('CREATE TABLE ', str_create_table_with_squema)
        #     sqls[i] = sql
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs creation project: {}, error:\n{}'
                         .format(project_name, str_error))
            return str_error, definition_is_saved
        self.sqls_to_process.clear()

        # save project definition
        str_error = super().save_project_definition(update = False, db_schema = db_schema)
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs saving project definition: {}, error:\n{}'
                         .format(project_name, str_error))
            return str_error, definition_is_saved
        # self.db_project = db_project
        # self.db_schema = db_schema
        return str_error, definition_is_saved

    def get_map_views(self):
        map_views_with_prefix = self.map_views.keys()
        map_views_without_prefix = []
        for map_view_with_prefix in map_views_with_prefix:
            map_view_without_prefix = map_view_with_prefix.replace(self.layer_name_prefix, '')
            map_views_without_prefix.append(map_view_without_prefix)
        return map_views_without_prefix

    def load_map_views(self):
        str_error = ''
        if not defs_server_api.PROJECT_TAG_WFS_SERVICE in self.db_project:
            str_error = ('Not exists tag: {} in db_project'.format(defs_server_api.PROJECT_TAG_WFS_SERVICE))
            return str_error
        wfs_service = self.db_project[defs_server_api.PROJECT_TAG_WFS_SERVICE]
        wfs_url = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_URL]
        wfs_user = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_USER]
        wfs_password = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_PASSWORD]
        return super().load_map_views(wfs = [wfs_url, wfs_user, wfs_password])

    def open(self, project_name):
        str_error = ''
        str_error, db_project = self.pgs_connection.get_project_by_name(project_name)
        if str_error:
            str_error = ('Recovering created project: {}, error:\n{}'.format(project_name, str_error))
            return str_error
        project_id = db_project[defs_server_api.PROJECT_TAG_ID]
        db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error, db_project_data = self.pgs_connection.get_project_data(project_id)
        if str_error:
            str_error = ('Recovering project data: {}, error:\n{}'.format(project_name, str_error))
            return str_error

        # project definition
        str_error = super().load_project_definition(db_schema = db_schema)
        if str_error:
            str_error = ('For project: {}, error recovering SQLs to load project definition:\n{}'
                         .format(project_name, str_error))
            return str_error
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs load project definition: {}, error:\n{}'
                         .format(project_name, str_error))
            return str_error
        if not isinstance(data, list):
            str_error = ('Executing SQLs load project definition: {}, error:\n{}'
                         .format(project_name, 'Data must be a list'))
            return str_error
        if len(data) != 1:
            str_error = ('Executing SQLs load project definition: {}, error:\n{}'
                         .format(project_name, 'Data must be a list of length 1'))
            return str_error
        value = data[0][defs_project.MANAGEMENT_FIELD_CONTENT]
        # json_acceptable_string = value.replace("'", "\"")
        # management_json_content = json.loads(json_acceptable_string)
        project_definition_json_content = json.loads(value)
        str_error = self.set_definition_from_json(project_definition_json_content)
        if str_error:
            str_error = ('\nSetting definition for project: {}\nerror:\n{}'.format(project_name, str_error))
            return str_error
        self.sqls_to_process.clear()

        #locations
        self.db_project = db_project_data
        self.db_schema = db_schema
        self.layer_name_prefix = self.db_schema + ':'
        self.locations_layer_name = self.layer_name_prefix + defs_project.LOCATIONS_LAYER_NAME
        return str_error

    def remove_map_view(self,
                        map_view_id):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        if not defs_server_api.PROJECT_TAG_WFS_SERVICE in self.db_project:
            str_error = ('Not exists tag: {} in db_project'.format(defs_server_api.PROJECT_TAG_WFS_SERVICE))
            return str_error
        wfs_service = self.db_project[defs_server_api.PROJECT_TAG_WFS_SERVICE]
        wfs_url = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_URL]
        wfs_user = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_USER]
        wfs_password = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_PASSWORD]
        return super().remove_map_view(map_view_id, wfs = [wfs_url, wfs_user, wfs_password])

    def save(self):
        str_error = ''
        name = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_NAME]
        str_error, exists_project = self.pgs_connection.get_exists_project_by_name(name)
        if str_error:
            str_error = ('Recovering if exists project: {}, error:\n{}'.format(name, str_error))
            return str_error
        if exists_project:
            str_error = ('Project already exists:\n{}\nSet another name or remove previous project before'.format(name))
            return str_error
        tag = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_TAG]
        author = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_AUTHOR]
        crs_id = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_CRS]
        output_path = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH]
        description = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_DESCRIPTION]
        str_start_date = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_START_DATE]
        str_finish_date = self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_FINISH_DATE]
        start_date = QDate.fromString(str_start_date, defs_project_definition.QDATE_TO_STRING_FORMAT)
        finish_date = QDate.fromString(str_finish_date, defs_project_definition.QDATE_TO_STRING_FORMAT)
        start_date_time = QDateTime()
        start_date_time.setDate(start_date)
        finish_date_time = QDateTime()
        finish_date_time.setDate(finish_date)
        str_start_date_time = start_date_time.toString(defs_server_api.PROJECT_DATE_TIME_FORMAT)
        str_finish_date_time = finish_date_time.toString(defs_server_api.PROJECT_DATE_TIME_FORMAT)
        type = defs_server_api.PROJECT_TYPE_DEFAULT
        str_error = self.pgs_connection.create_project(name, description,
                                                       str_start_date_time, str_finish_date_time, type)
        if str_error:
            str_error = ('Error creating project:\n{}'.format(str_error))
            return str_error
        return str_error

    def update_db_project_data(self):
        str_error = ''
        project_name = self.db_project[defs_server_api.PROJECT_TAG_NAME]
        project_id = self.db_project[defs_server_api.PROJECT_TAG_ID]
        str_error, db_project_data = self.pgs_connection.get_project_data(project_id)
        if str_error:
            str_error = ('Updating project data: {}, error:\n{}'.format(project_name, str_error))
            return str_error
        self.db_project = db_project_data
        return str_error

    def update_map_view(self,
                        map_view_id,
                        map_view_wkb_geometry):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        if not defs_server_api.PROJECT_TAG_WFS_SERVICE in self.db_project:
            str_error = ('Not exists tag: {} in db_project'.format(defs_server_api.PROJECT_TAG_WFS_SERVICE))
            return str_error
        wfs_service = self.db_project[defs_server_api.PROJECT_TAG_WFS_SERVICE]
        wfs_url = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_URL]
        wfs_user = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_USER]
        wfs_password = wfs_service[defs_server_api.PROJECT_WFS_SERVICE_TAG_PASSWORD]
        update = True
        return super().save_map_view(map_view_id, map_view_wkb_geometry,
                                     update = update, wfs = [wfs_url, wfs_user, wfs_password])
