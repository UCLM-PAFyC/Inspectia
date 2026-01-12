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
from pyLibProject.defs import defs_layers_groups
from pyLibProject.defs import defs_layers
from pyLibGisApi.lib.PostGISServerAPI import PostGISServerAPI
from pyLibGisApi.defs import defs_server_api
from pyLibProcesses.defs import defs_project as processes_defs_project
from pyLibProcesses.defs import defs_processes as processes_defs_processes

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

        # create layers_groups
        for layers_group_name in defs_layers_groups.fields_by_layers_group:
            layers_group = defs_layers_groups.fields_by_layers_group[layers_group_name]
            layers_group_name = layers_group[defs_layers_groups.LAYERS_GROUP_FIELD_NAME]
            str_error, layers_group_db_id = self.pgs_connection.get_layers_group_id_by_name(project_id, layers_group_name)
            if layers_group_db_id is None:
                str_error = self.pgs_connection.create_layers_group(project_id, layers_group)
                if str_error:
                    str_error = ('In project: {}\ncreating layers group: {}\nerror:\n{}'
                                 .format(project_name, layers_group_name, str_error))
                    return str_error, definition_is_saved

        # publish layers
        for layer_name in defs_layers.fields_by_layer:
            layer = defs_layers.fields_by_layer[layer_name]
            layer_table_name = layer[defs_layers.LAYER_FIELD_TABLE_NAME]
            str_error, layer_db_id = self.pgs_connection.get_layer_id_by_table_name(project_id, layer_table_name)
            if layer_db_id is None:
                sld_content = None
                if layer_table_name in defs_project.sld_file_path_by_layer:
                    sld_file_path = defs_project.sld_file_path_by_layer[layer_table_name]
                    if os.path.exists(sld_file_path):
                        str_error = ''
                        try:
                            with open(sld_file_path, 'r') as f:
                                sld_content = f.read()
                        except IOError as e:
                            str_error = ('Reading SLD file:\n{}\nI/O error({}): {}'
                                         .format(sld_file_path, e.errno, e.strerror))
                        except:  # handle other exceptions such as attribute errors
                            str_error = ('Reading SLD file:\n{}\nUnexpected error: {}'
                                         .format(sld_file_path, sys.exc_info()[0]))
                        if str_error:
                            str_error = ('In project: {}\ncreating layer: {}\nerror:\n{}'
                                         .format(project_name, layer_table_name, str_error))
                            return str_error, definition_is_saved
                if sld_content:
                    # sld_content = sld_content.replace('"', '\\"')
                    sld_content = sld_content.replace('\n', '')
                    layer[defs_layers.LAYER_SLD_CONTENT] = sld_content
                layers_group_db_id = None
                if layer_table_name in defs_layers.layers_group_name_by_layer:
                    layers_group_name = defs_layers.layers_group_name_by_layer[layer_table_name]
                    str_error, layers_group_db_id = self.pgs_connection.get_layers_group_id_by_name(project_id,
                                                                                                    layers_group_name)
                if layers_group_db_id is not None:
                    layer[defs_layers.LAYERS_GROUP_ID] = layers_group_db_id
                str_error = self.pgs_connection.create_layer(project_id, layer)
                if str_error:
                    str_error = ('In project: {}\ncreating layer: {}\nerror:\n{}'
                                 .format(project_name, layer_table_name, str_error))
                    return str_error, definition_is_saved
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

        # project processes
        str_error = super().load_processes(db_schema = db_schema)
        if str_error:
            str_error = ('For project: {}, error recovering SQLs to load processes:\n{}'
                         .format(project_name, str_error))
            return str_error
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs load processes: {}, error:\n{}'
                         .format(project_name, str_error))
            return str_error
        if not data is None:
            if not isinstance(data, list):
                str_error = ('Executing SQLs load processes: {}, error:\n{}'
                             .format(project_name, 'Data must be a list'))
                return str_error
            for feature in data:
                process_label = feature[processes_defs_project.PROCESESS_FIELD_LABEL]
                process_dict = {}
                for field_name in processes_defs_project.fields_by_layer[processes_defs_project.PROCESESS_LAYER_NAME]:
                    if field_name == processes_defs_project.PROCESESS_FIELD_GEOMETRY:
                        continue
                    field_value = ''
                    if field_name in feature:
                        field_value = feature[field_name]
                    process_dict[field_name] = field_value
                if process_label in self.process_by_label:
                    self.process_by_label.pop(process_label)
                self.process_by_label[process_label] = process_dict
        self.sqls_to_process.clear()

        return str_error

    def project_definition_gui(self,
                               is_process_creation,
                               parent_widget = None):
        return super().project_definition_gui(is_process_creation, parent_widget)

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

    def remove_process(self,
                       process_label):
        str_error = ''
        project_name = self.db_project[defs_server_api.PROJECT_TAG_NAME]
        project_id = self.db_project[defs_server_api.PROJECT_TAG_ID]
        db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error = super().remove_process(process_label,
                                           db_schema = db_schema)
        if str_error:
            str_error = ('For project: {}, recovering SQLs to remove process:\n{}\nerror:\n{}'
                         .format(project_name, process_label, str_error))
            return str_error
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs to remove process: {},\nerror:\n{}'
                         .format(project_name, process_label, str_error))
            return str_error
        self.process_by_label.pop(process_label)
        self.sqls_to_process.clear()

    def save(self, is_process_creation = True):
        str_error = ''
        if not is_process_creation:
            project_name = self.db_project[defs_server_api.PROJECT_TAG_NAME]
            project_id = self.db_project[defs_server_api.PROJECT_TAG_ID]
            db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
            str_error = super().save_project_definition(update = True, db_schema = db_schema)
            sqls = self.sqls_to_process
            str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
            if str_error:
                str_error = ('Executing SQLs saving project definition: {}, error:\n{}'
                             .format(project_name, str_error))
                return str_error
        else:
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

    def save_process(self,
                     process_content,
                     process_author,
                     process_label,
                     process_description,
                     process_log,
                     process_date_time_as_string,
                     process_output,
                     process_remarks):
        str_error = ''
        self.sqls_to_process.clear()
        project_name = self.db_project[defs_server_api.PROJECT_TAG_NAME]
        project_id = self.db_project[defs_server_api.PROJECT_TAG_ID]
        db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error = super().save_process(process_content,
                                         process_author,
                                         process_label,
                                         process_description,
                                         process_log,
                                         process_date_time_as_string,
                                         process_output,
                                         process_remarks,
                                         file_path=None,
                                         db_schema=db_schema)
        if str_error:
            return str_error
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs saving process: {}, error:\n{}'
                         .format(process_label, str_error))
            return str_error
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_LABEL] = process_label
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_AUTHOR] = process_author
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_DESCRIPTION] = process_description
        self.process_by_label[process_label][
            processes_defs_project.PROCESESS_FIELD_DATE_TIME] = process_date_time_as_string
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_PROCESS_CONTENT] = process_content
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_LOG] = process_log
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_OUTPUT] = process_output
        self.process_by_label[process_label][processes_defs_project.PROCESESS_FIELD_REMARKS] = process_remarks
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

    def update_process(self,
                       original_label,
                       process_label):
        str_error = ''
        project_name = self.db_project[defs_server_api.PROJECT_TAG_NAME]
        project_id = self.db_project[defs_server_api.PROJECT_TAG_ID]
        db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error = super().update_process(original_label,
                                           process_label,
                                           db_schema = db_schema)
        if str_error:
            str_error = ('For project: {}, recovering SQLs to update process:\n{}\nerror:\n{}'
                         .format(project_name, process_label, str_error))
            return str_error
        sqls = self.sqls_to_process
        str_error, data = self.pgs_connection.execute_sqls(project_id, sqls)
        if str_error:
            str_error = ('Executing SQLs to update process: {},\nerror:\n{}'
                         .format(project_name, process_label, str_error))
            return str_error
        self.sqls_to_process.clear()
