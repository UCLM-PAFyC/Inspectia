# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
import shutil
import pathlib
import json

from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QFileDialog, QPushButton, QComboBox,
                             QInputDialog, QLineEdit)
from PyQt5.QtCore import QDir, QFileInfo, QFile, Qt
from PyQt5.QtGui import QStandardItem, QColor

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from Inspectia.defs import defs_paths
from Inspectia.defs import defs_main
from Inspectia.defs import defs_qsettings
from Inspectia.defs import defs_processes as app_defs_processes

common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from Inspectia.lib.ProjectInspectia import ProjectInspectia

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from pyLibProcesses.defs import defs_processes
from pyLibProcesses.defs import defs_project as processes_defs_project
from pyLibProcesses.ProcessesManager import ProcessesManager
from pyLibProcesses.gui.ProcessesManagerDialog import ProcessesManagerDialog
from pyLibProcesses.gui.ProjectProcessesDialog import ProjectProcessesDialog
from pyLibQtTools import Tools
from pyLibQtTools.LoginDialog import LoginDialog
from pyLibGisApi.lib.PostGISServerAPI import PostGISServerConnection
from pyLibGisApi.defs import defs_server_api
from pyLibGisApi.defs import defs_processes as postgis_api_defs_processes
from pyLibQtTools.Tools import SimpleTextEditDialog
from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibParameters.ui_qt.ParametersManagerDialog import ParametersManagerDialog
from pyLibQtTools.QProcessDialog import QProcessDialog
from pyLibQtTools import defs_qprocess
# from pyLibQtTools.multipleFileSelectorDialog.multiple_file_selector_dialog import MultipleFileSelectorDialog


class InspectiaDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 settings,
                 main_path,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'InspectiaDialog.ui'), self)
        self.settings = settings
        self.main_path = main_path
        self.project = None
        self.qgis_iface = None
        self.processes_manager = None
        self.process_author_value = ''
        self.process_label_value = ''
        self.process_description_value = ''
        self.gis_server_api_url = None
        self.gis_server_api_email = None
        self.gis_server_api_password = None
        self.gis_server_api_token = None
        self.pgs_connection = None
        self.user_is_owner = False
        self.user_is_admin = False
        self.user_is_editor = False
        self.user_is_user = False
        self.role_by_project_user = {}
        self.initialize()

    def add_role_to_user(self):
        str_error = ''
        project_id = self.project.db_project[defs_server_api.PROJECT_TAG_ID]
        project_name = self.project.db_project[defs_server_api.PROJECT_TAG_NAME]
        user_email = self.userComboBox.currentText()
        user_role = self.roleComboBox.currentText()
        user_id = None
        for db_user_email in self.pgs_connection.user_by_email:
            if db_user_email.casefold() == user_email:
                user_id = self.pgs_connection.user_by_email[db_user_email][defs_server_api.USERS_TAG_ID]
                break
        if user_id is None: # never
            return str_error
        str_error = self.pgs_connection.add_user_to_project(project_id, user_id, user_role)
        if str_error:
            str_error = ('Adding user: {} to project: {}, error:\n{}'.format(user_email, project_name, str_error))
            return str_error
        str_error = self.project.update_db_project_data()
        if str_error:
            str_error = ('Adding user: {} to project: {}, error:\n{}'.format(user_email, project_name, str_error))
            return str_error
        self.update_user_management()
        return str_error

    def close_project(self):
        del self.project
        self.project = None
        self.projectComboBox.setEnabled(True)
        self.projectComboBox.setCurrentIndex(0)
        # self.projectDefinitionPushButton.setEnabled(False)
        # self.openProjectPushButton.setEnabled(True)
        # self.closeProjectPushButton.setEnabled(False)
        # self.deleteProjectPushButton.setEnabled(True)
        return

    def delete_project(self):
        if self.pgs_connection is None:
            str_msg = ("Login before")
            Tools.info_msg(str_msg)
            return
        project_name = self.projectComboBox.currentText()
        if not self.project is None:
            del self.project
            self.project = None
        str_error = self.pgs_connection.delete_project_by_name(project_name)
        if str_error:
            str_error = ('Deleting project: {}, error:\n{}'.format(project_name, str_error))
            Tools.info_msg(str_error)
            return
        self.update_project_management()
        return

    def initialize(self):
        self.crs_tools = CRSsTools()
        # process_path_by_provider = {}
        # for provider in app_defs_processes.processes_providers:
        #     process_path_by_provider[provider] = []
        #     process_path_by_provider[provider].append(app_defs_processes.processes_path)
        # for provider in postgis_api_defs_processes.processes_providers:
        #     if not provider in process_path_by_provider:
        #         process_path_by_provider[provider] = []
        #     process_path_by_provider[provider].append(postgis_api_defs_processes.processes_path)
        # processes_manager = ProcessesManager()
        # str_error = processes_manager.initialize(process_path_by_provider)
        # if str_error:
        #     Tools.error_msg(str_error)
        #     return
        # self.processes_manager = processes_manager
        # self.processesManagerPushButton.clicked.connect(self.select_processes_manager_gui)
        processes_manager = ProcessesManager()
        str_error = processes_manager.initialize(app_defs_processes.process_path_by_provider,
                                                 app_defs_processes.ignored_process_name_by_provider)
        if str_error:
            Tools.error_msg(str_error)
            return
        self.processes_manager = processes_manager
        self.processesManagerPushButton.clicked.connect(self.select_processes_manager_gui)

        self.pgs_connection = PostGISServerConnection(self.settings)
        self.last_path = self.settings.value(defs_qsettings.QSETTINGS_TAG_LAST_PATH)
        current_dir = QDir.current()
        if not self.last_path:
            self.last_path = QDir.currentPath()
            self.settings.setValue(defs_qsettings.QSETTINGS_TAG_LAST_PATH, self.last_path)
            self.settings.sync()
        self.gis_server_api_url = self.settings.value(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_URL)
        if not self.gis_server_api_url:
            self.gis_server_api_url = defs_main.GIS_SERVER_API_URL_DEFAULT
            self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_URL, self.gis_server_api_url)
            self.settings.sync()
        self.gis_server_api_email = self.settings.value(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_EMAIL)
        if not self.gis_server_api_email:
            self.gis_server_api_email = defs_main.GIS_SERVER_API_EMAIL_DEFAULT
            self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_EMAIL, self.gis_server_api_email)
            self.settings.sync()
        self.gis_server_api_password = self.settings.value(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_PASSWORD)
        if not self.gis_server_api_password:
            self.gis_server_api_password = defs_main.GIS_SERVER_API_PASSWORD_DEFAULT
            self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_PASSWORD, self.gis_server_api_password)
            self.settings.sync()
        self.gis_server_api_token = self.settings.value(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_TOKEN)
        self.setWindowTitle(defs_main.MAIN_WIDGET_TITLE)
        self.registerPushButton.clicked.connect(self.register)
        self.loginPushButton.clicked.connect(self.login)
        self.logoutPushButton.clicked.connect(self.logout)
        self.logoutPushButton.setEnabled(False)
        self.projectComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.projectRoleLineEdit.setEnabled(False)
        self.projectComboBox.currentIndexChanged.connect(self.select_project)
        self.closeProjectPushButton.clicked.connect(self.close_project)
        self.deleteProjectPushButton.clicked.connect(self.delete_project)
        self.newProjectPushButton.clicked.connect(self.new_project)
        self.openProjectPushButton.clicked.connect(self.open_project)
        self.projectDefinitionPushButton.clicked.connect(self.project_definition)
        self.userComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.roleComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.roleComboBox.addItem(defs_server_api.ROLE_ADMIN)
        self.roleComboBox.addItem(defs_server_api.ROLE_EDITOR)
        self.roleComboBox.addItem(defs_server_api.ROLE_USER)
        self.userComboBox.currentIndexChanged.connect(self.select_user)
        self.roleComboBox.currentIndexChanged.connect(self.select_role)
        self.addRoleToUserPushButton.clicked.connect(self.add_role_to_user)
        self.removeRoleToUserPushButton.clicked.connect(self.remove_role_to_user)
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.mapViewsComboBox.currentIndexChanged.connect(self.select_map_view)
        self.setMapViewPushButton.clicked.connect(self.set_map_view)
        self.removeMapViewPushButton.clicked.connect(self.remove_map_view)
        self.updateFromMapViewPushButton.clicked.connect(self.update_map_view)
        self.newFromMapViewPushButton.clicked.connect(self.new_map_view)

        # processes
        self.processComboBox.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.processComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.processComboBox.currentIndexChanged.connect(self.process_changed)
        self.processesDbPushButton.clicked.connect(self.processes_db)
        self.processParametersPushButton.clicked.connect(self.process_parameters)
        self.processLabelPushButton.clicked.connect(self.process_label)
        self.processAuthorPushButton.clicked.connect(self.process_author)
        self.processDescriptionPushButton.clicked.connect(self.process_description)
        self.processRunPushButton.clicked.connect(self.process_run)
        # self.processesDbPushButton.setEnabled(False)
        # self.processParametersPushButton.setEnabled(False)
        # self.processLabelPushButton.setEnabled(False)
        # self.processAuthorPushButton.setEnabled(False)
        # self.processDescriptionPushButton.setEnabled(False)
        # self.processRunPushButton.setEnabled(False)

        self.toolBox.setEnabled(False)
        # self.toolBox.setItemEnabled(0, False)
        # self.toolBox.setItemEnabled(1, False)
        # if self.qgis_iface is None:
        #     self.locationsGroupBox.setEnabled(False)
        return

    def login(self):
        self.close_project()
        self.toolBox.setEnabled(False)
        # self.toolBox.setItemEnabled(0, False)
        title = 'Login in Inspectia'
        url = self.gis_server_api_url
        email = self.gis_server_api_email
        password = self.gis_server_api_password
        is_register = False
        dialog = LoginDialog(self, title, email, password, url, is_register)
        dialog_result = dialog.exec()
        if not dialog_result == QDialog.Accepted:
            str_error = ('Not logged')
            Tools.error_msg(str_error)
            if self.gis_server_api_email is None:
                self.toolBox.setItemEnabled(0, False)
                self.update_project_management()
            return
        email = dialog.email
        password = dialog.password
        url = dialog.url
        str_error = self.pgs_connection.login(url, email, password)
        # str_error = self.project.login(url, username, password)
        if str_error:
            str_error = ('Error logging:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            self.gis_server_api_password = None
            self.loginPushButton.setEnabled(True)
            self.logoutPushButton.setEnabled(False)
            self.registerPushButton.setEnabled(True)
            self.close_project()
            # self.update_project_management()
            self.toolBox.setItemEnabled(0, False)
            # self.update_project_management()
            # if self.gis_server_api_email is None:
            #     self.toolBox.setItemEnabled(0, False)
            #     # self.update_project_management()
            return
        self.toolBox.setItemEnabled(0, True)
        self.gis_server_api_url = url
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_URL, self.gis_server_api_url)
        self.gis_server_api_email = email
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_EMAIL, self.gis_server_api_email)
        self.gis_server_api_password = password
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_PASSWORD, self.gis_server_api_password)
        self.settings.sync()
        self.toolBox.setEnabled(True)
        # self.toolBox.setItemEnabled(0, True)
        self.update_project_management()
        self.toolBox.setCurrentIndex(0)
        self.loginPushButton.setEnabled(False)
        self.logoutPushButton.setEnabled(True)
        self.registerPushButton.setEnabled(False)
        return

    def logout(self):
        self.gis_server_api_password = None
        self.close_project()
        self.projectComboBox.currentIndexChanged.disconnect(self.select_project)
        self.projectComboBox.clear()
        self.projectComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.projectComboBox.currentIndexChanged.connect(self.select_project)
        self.projectComboBox.setEnabled(False)
        self.newProjectPushButton.setEnabled(False)
        self.loginPushButton.setEnabled(True)
        self.logoutPushButton.setEnabled(False)
        self.registerPushButton.setEnabled(True)
        return

    def new_map_view(self):
        if not self.qgis_iface:
            return
        str_error, wkb_geometry = self.qgis_iface.get_map_canvas_wkb_geometry_in_project_crs()
        if str_error:
            str_error = ('Getting map canvas WKB geometry, error:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        text, okPressed = QInputDialog.getText(self, "Location name", "Enter name:",
                                               QLineEdit.Normal)
        if okPressed and text != '':
            if text in self.project.get_map_views():
                str_error = ('Exists a previous location with name: {}'.format(text))
                Tools.error_msg(str_error)
                return
            str_error = self.project.add_map_view(text, wkb_geometry)
            if str_error:
                Tools.error_msg(str_error)
                return
            # self.update_map_views(text)
            self.update_map_views()
        else:
            str_error = ('You must enter a valid location name')
            Tools.error_msg(str_error)
            return
        return

    def new_project(self):
        if self.pgs_connection is None:
            str_msg = ("Login before")
            Tools.info_msg(str_msg)
            return
        if not self.project is None:
            del self.project
            self.project = None
        self.project = ProjectInspectia(self.qgis_iface, self.settings, self.crs_tools, self.pgs_connection)
        str_error, definition_is_saved = self.project.create(self)
        if str_error:
            str_error = ('Error creating project:\n{}'.format(str_error))
            Tools.info_msg(str_error)
            return
        if not definition_is_saved:
            del self.project
            self.project = None
        self.update_project_management()
        return

    def open_project(self):
        self.projectDefinitionPushButton.setEnabled(False)
        self.openProjectPushButton.setEnabled(True)
        self.closeProjectPushButton.setEnabled(False)
        self.deleteProjectPushButton.setEnabled(True)
        self.role_by_project_user.clear()
        if self.pgs_connection is None:
            str_msg = ("Login before")
            Tools.info_msg(str_msg)
            return
        if not self.project is None:
            del self.project
            self.project = None
        self.project = ProjectInspectia(self.qgis_iface, self.settings, self.crs_tools, self.pgs_connection)
        project_name = self.projectComboBox.currentText()
        str_error = self.project.open(project_name)
        if str_error:
            str_error = ('Error creating project:\n{}'.format(str_error))
            Tools.info_msg(str_error)
            return
        self.projectComboBox.setEnabled(False)
        self.projectDefinitionPushButton.setEnabled(True)
        self.openProjectPushButton.setEnabled(False)
        self.closeProjectPushButton.setEnabled(True)
        self.deleteProjectPushButton.setEnabled(False)
        if self.user_is_owner or self.user_is_admin:
            self.usersManagementGroupBox.setEnabled(True)
            self.update_user_management()
        else:
            self.usersManagementGroupBox.setEnabled(False)
        self.locationsGroupBox.setEnabled(True)
        self.update_map_views()
        self.processesGroupBox.setEnabled(True)
        self.processInformationGroupBox.setEnabled(False)
        return

    def process_author(self):
        current_text = self.process_author_value
        title = "Enter process author"
        text, ok = QInputDialog().getText(self, title,
                                          "Process author:", QLineEdit.Normal,
                                          current_text)
        if ok and text:
            self.process_author_value = text
        return

    def process_changed(self):
        self.processParametersPushButton.setEnabled(False)
        self.processLabelPushButton.setEnabled(False)
        self.processAuthorPushButton.setEnabled(False)
        self.processDescriptionPushButton.setEnabled(False)
        self.processRunPushButton.setEnabled(False)
        process = self.processComboBox.currentText()
        if process != defs_main.NO_COMBO_SELECT:
            self.processParametersPushButton.setEnabled(True)
            self.processLabelPushButton.setEnabled(True)
            self.processAuthorPushButton.setEnabled(True)
            self.processDescriptionPushButton.setEnabled(True)
            self.processRunPushButton.setEnabled(True)

    def processes_db(self):
        title = processes_defs_project.PROJECT_PROCESSES_DIALOG_TITLE
        dialog = ProjectProcessesDialog(self.project, title, self.settings, self)
        dialog_result = dialog.exec()
        return

    def process_description(self):
        current_text = self.process_description_value
        title = "Enter process description"
        dialog = SimpleTextEditDialog(title, current_text, False)
        ret = dialog.exec()
        # if ret == QDialog.Accepted:
        #     text = dialog.get_text()
        #     self.descriptionLineEdit.setText(text)
        text = dialog.get_text()
        if text != current_text:
            self.process_description_value = text
        return

    def process_label(self):
        current_text = self.process_label_value
        title = "Enter process label"
        text, ok = QInputDialog().getText(self, title,
                                          "Process label (unique value):", QLineEdit.Normal,
                                          current_text)
        if ok and text:
            self.process_label_value = text
        return

    def process_parameters(self):
        process_name = self.processComboBox.currentText()
        if process_name == defs_main.NO_COMBO_SELECT:
            return
        process = None
        for process_provider in self.processes_manager.processes_by_provider:
            if process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                break
        if not process:
            return
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        process_file_path = process[defs_processes.PROCESS_FILE]
        title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
        dialog = ParametersManagerDialog(parametes_manager, title, self.qgis_iface, self.settings, self)
        dialog_result = dialog.exec()
        return

    def process_run(self):
        if not self.process_author_value:
            msg = ("Input process author")
            Tools.info_msg(msg)
            return
        if not self.process_description_value:
            msg = ("Input process description")
            Tools.info_msg(msg)
            return
        if not self.process_label_value:
            msg = ("Input process label")
            Tools.info_msg(msg)
            return
        if self.process_label_value in self.project.process_by_label:
            msg = ("Exists another process with label: {}".format(self.process_label_value))
            msg += ("\nChange the label for new process,")
            msg += ("\nchange the label in the existing process ")
            msg += ("\nor remove the existing process")
            Tools.info_msg(msg)
            return
        process_name = self.processComboBox.currentText()
        if process_name == defs_main.NO_COMBO_SELECT:
            return
        process = None
        process_provider = None
        for process_provider in self.processes_manager.processes_by_provider:
            if process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                break
        if not process:
            return
        str_error, output_arguments = self.processes_manager.get_process_output_arguments(process_provider,
                                                                                          process_name)
        if str_error:
            Tools.error_msg(str_error)
            return
        output_as_json_str = json.dumps(output_arguments)
        process_log = None
        process_date_time_as_string = None
        # self.update_objects_fully_qualified_names()
        # if isinstance(process[defs_processes.PROCESS_FIELD_SRC], dict):
        #     if not defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS in process[defs_processes.PROCESS_FIELD_SRC]:
        #         msg = ("Not exists {} attribute in src".format(defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS))
        #         msg += ("\nfor proccess: {}".format(process_name))
        #         Tools.info_msg(msg)
        #         return
        #     if not defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD in process[defs_processes.PROCESS_FIELD_SRC]:
        #         msg = ("Not exists {} attribute in src".format(defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD))
        #         msg += ("\nfor proccess: {}".format(process_name))
        #         Tools.info_msg(msg)
        #         return
        #     object_fully_qualified_name = process[defs_processes.PROCESS_FIELD_SRC][defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS]
        #     object_method_name = process[defs_processes.PROCESS_FIELD_SRC][defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD]
        #     object_fully_qualified_name = object_fully_qualified_name.lower()
        #     # object_method_name = object_method_name.lower()
        #     if not object_fully_qualified_name in self.object_by_fully_qualified_name:
        #         msg = ("Not exists registered object: {}".format(object_fully_qualified_name))
        #         msg += ("\nfor proccess: {}".format(process_name))
        #         Tools.info_msg(msg)
        #         return
        #     object = self.object_by_fully_qualified_name[object_fully_qualified_name]
        #     if object is None:
        #         msg = ("None object: {}".format(object_fully_qualified_name))
        #         msg += ("\nfor proccess: {}".format(process_name))
        #         Tools.info_msg(msg)
        #         return
        #     method = None
        #     try:
        #         method = getattr(object, object_method_name)
        #     except AttributeError as e:
        #         msg = ("For proccess: {}".format(process_name))
        #         msg += ("\nError: {}".format(str(e)))
        #         Tools.info_msg(msg)
        #         return
        #     if method is None:
        #         msg = ("No found method: {} in object: {}".format(object_method_name, object_fully_qualified_name))
        #         msg += ("\nfor proccess: {}".format(process_name))
        #         Tools.info_msg(msg)
        #         return
        #     # str_error = object.run_library_process(process, self)
        #     str_error, end_date_time, log = method(process, self)
        #     if str_error:
        #         Tools.error_msg(str_error)
        #         return
        #     process_log = ''
        #     if not log is None:
        #         process_log = log
        #     process_date_time_as_string = None
        #     if end_date_time is not None:
        #         process_date_time_as_string = end_date_time.strftime(defs_main.DATE_TIME_STRING_FORMAT)
        # else:
        #     str_error, arguments = self.processes_manager.get_process_arguments(process_provider, process_name)
        #     if str_error:
        #         Tools.error_msg(str_error)
        #         return
        #     arguments.append('--' + defs_qprocess.ARGPARSER_TAG_STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS)
        #     arguments.append('\"' + defs_qprocess.STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS_DEFAULT + '\"')
        #     arguments.append('--' + defs_qprocess.ARGPARSER_TAG_STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE)
        #     arguments.append('\"' + defs_qprocess.STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE_DEFAULT + '\"')
        #     str_arguments = ""
        #     for i in range(len(arguments)):
        #         if i > 0:
        #             str_arguments += ' '
        #         if isinstance(arguments[i], str):
        #             str_arguments += arguments[i]
        #         else:
        #             str_arguments += str(arguments[i])
        #     program = defs_processes.PROCESS_PYTHON_PROGRAM
        #     title = ("Program: {}".format(program, arguments))
        #     dialog = QProcessDialog(title, self)
        #     dialog.start_process(program, arguments,
        #                          defs_qprocess.STRING_TO_PUBLISH_THE_NUMBER_OF_STEPS_DEFAULT,
        #                          defs_qprocess.STRING_TO_PUBLISH_COMPLETED_STEPS_PERCENTAGE_DEFAULT)
        #     dialog_result = dialog.exec()
        #     process_date_time_as_string = dialog.get_end_date_time_as_string(defs_main.DATE_TIME_STRING_FORMAT)
        #     process_log = dialog.get_log()
        # process_content_as_json = {}
        # process_content_as_json[defs_processes.PROCESS_FIELD_NAME] = process[defs_processes.PROCESS_FIELD_NAME]
        # process_content_as_json[defs_processes.PROCESS_FIELD_CONTRIBUTIONS] = process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
        # process_content_as_json[defs_processes.PROCESS_FIELD_SRC] = process[defs_processes.PROCESS_FIELD_SRC]
        # process_content_as_json[defs_processes.PROCESS_FIELD_DESCRIPTION] = process[defs_processes.PROCESS_FIELD_DESCRIPTION]
        # process_content_as_json[defs_processes.PROCESS_FIELD_DOC] = process[defs_processes.PROCESS_DOC]
        # process_content_as_json[defs_processes.PROCESS_FIELD_PARAMETERS] \
        #     = process[defs_processes.PROCESS_FIELD_PARAMETERS].parameters_as_list_of_dict
        # process_content_as_json[defs_processes.PROCESS_FIELD_DOC] = process[defs_processes.PROCESS_DOC]
        # process_content_as_json = json.dumps(process_content_as_json, indent=4, ensure_ascii=False)
        # process_content = process_content_as_json
        # process_output = output_as_json_str
        # process_remarks = ''
        # str_error = self.project.save_process(process_content,
        #                                       self.process_author_value,
        #                                       self.process_label_value,
        #                                       self.process_description_value,
        #                                       process_log,
        #                                       process_date_time_as_string,
        #                                       process_output,
        #                                       process_remarks)
        # if str_error:
        #     Tools.error_msg(str_error)
        #     return
        # else:
        #     str_msg = "Process completed successfully"
        #     Tools.info_msg(str_msg)
        # if self.qgis_iface:
        #     str_error = self.qgis_iface.reload_all_layers()
        #     if str_error:
        #         Tools.error_msg(str_error)
        #         return
        return

    def project_definition(self,
                           is_process_creation = False):
        if not self.project:
            str_error = ('Not exists project')
            Tools.error_msg(str_error)
            return False
        str_error, definition_is_saved = self.project.project_definition_gui(is_process_creation, self)
        if str_error:
            str_error = ('Project definition, error:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return False
        return definition_is_saved

    def register(self):
        title = 'Register in Inspectia'
        url = self.gis_server_api_url
        email = ''#self.gis_server_api_username
        password = ''#self.gis_server_api_password
        is_register = True
        dialog = LoginDialog(self, title, email, password, url, is_register)
        dialog_result = dialog.exec()
        if not dialog_result == QDialog.Accepted:
            str_error = ('Not registered')
            Tools.error_msg(str_error)
            return
        name = dialog.name
        email = dialog.email
        password = dialog.password
        url = dialog.url
        str_error = self.pgs_connection.register(url, name, email, password)
        # str_error = self.project.login(url, username, password)
        if str_error:
            str_error = ('Error registering:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        return

    def remove_map_view(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error = self.project.remove_map_view(map_view_id)
        if str_error:
            Tools.error_msg(str_error)
        self.update_map_views()
        return

    def remove_role_to_user(self):
        str_error = ''
        project_id = self.project.db_project[defs_server_api.PROJECT_TAG_ID]
        project_name = self.project.db_project[defs_server_api.PROJECT_TAG_NAME]
        user_email = self.userComboBox.currentText()
        user_id = None
        for db_user_email in self.pgs_connection.user_by_email:
            if db_user_email.casefold() == user_email:
                user_id = self.pgs_connection.user_by_email[db_user_email][defs_server_api.USERS_TAG_ID]
                break
        if user_id is None: # never
            return str_error
        str_error = self.pgs_connection.remove_user_from_project(project_id, user_id)
        if str_error:
            str_error = ('Removing user: {} from project: {}, error:\n{}'.format(user_email, project_name, str_error))
            return str_error
        str_error = self.project.update_db_project_data()
        if str_error:
            str_error = ('Removing user: {} from project: {}, error:\n{}'.format(user_email, project_name, str_error))
            return str_error
        self.update_user_management()
        return str_error

    def select_map_view(self):
        map_view = self.mapViewsComboBox.currentText()
        if map_view == defs_main.NO_COMBO_SELECT:
            self.updateFromMapViewPushButton.setEnabled(False)
            self.removeMapViewPushButton.setEnabled(False)
            self.newFromMapViewPushButton.setEnabled(True)
            self.setMapViewPushButton.setEnabled(False)
        else:
            self.updateFromMapViewPushButton.setEnabled(True)
            self.removeMapViewPushButton.setEnabled(True)
            self.newFromMapViewPushButton.setEnabled(True)
            self.setMapViewPushButton.setEnabled(True)
        return

    def select_processes_manager_gui(self):
        str_error = ""
        title = defs_processes.PROCESSES_MANAGER_DIALOG_TITLE
        dialog = ProcessesManagerDialog(self.processes_manager, title, self.qgis_iface, self.settings, self)
        dialog_result = dialog.exec()
        # if dialog_result != QDialog.Accepted:
        #     return str_error
        # Tools.error_msg(str_error)
        return str_error

    def select_project(self):
        self.user_is_owner = False
        self.user_is_admin = False
        self.user_is_editor = False
        self.user_is_user = False
        project_name = self.projectComboBox.currentText()
        self.projectRoleLineEdit.clear()
        if project_name == defs_main.NO_COMBO_SELECT:
            self.openProjectPushButton.setEnabled(False)
            self.closeProjectPushButton.setEnabled(False)
            self.newProjectPushButton.setEnabled(True)
            self.deleteProjectPushButton.setEnabled(False)
            self.projectRoleLineEdit.setEnabled(False)
            self.projectDefinitionPushButton.setEnabled(False)
        else:
            str_error, project_role = self.pgs_connection.get_project_role_by_name(project_name)
            if str_error:
                str_error = ('Getting role for project: {}, error:\n{}'.format(project_name, str_error))
                Tools.error_msg(str_error)
                self.projectComboBox.setCurrentIndex(0)
                return
            self.projectRoleLineEdit.setEnabled(True)
            self.openProjectPushButton.setEnabled(True)
            self.closeProjectPushButton.setEnabled(False)
            self.newProjectPushButton.setEnabled(False)
            if project_role.casefold() == defs_server_api.ROLE_OWNER.casefold():
                self.user_is_owner = True
            elif project_role.casefold() == defs_server_api.ROLE_ADMIN.casefold():
                self.user_is_admin = True
            elif project_role.casefold() == defs_server_api.ROLE_EDITOR.casefold():
                self.user_is_editor = True
            elif project_role.casefold() == defs_server_api.ROLE_USER.casefold():
                self.user_is_user = True
            if self.user_is_owner:
                self.deleteProjectPushButton.setEnabled(True)
            self.projectRoleLineEdit.setText(project_role)
            self.projectDefinitionPushButton.setEnabled(False)
            if self.user_is_owner:
                self.deleteProjectPushButton.setEnabled(True)
            else:
                self.deleteProjectPushButton.setEnabled(False)
        self.userComboBox.currentIndexChanged.disconnect(self.select_user)
        self.userComboBox.clear()
        self.userComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.userComboBox.setCurrentIndex(0)
        self.roleComboBox.setCurrentIndex(0)
        self.roleComboBox.setEnabled(False)
        self.addRoleToUserPushButton.setEnabled(False)
        self.removeRoleToUserPushButton.setEnabled(False)
        self.userComboBox.currentIndexChanged.connect(self.select_user)
        self.userComboBox.setEnabled(False)
        self.roleComboBox.setEnabled(False)
        self.usersManagementGroupBox.setEnabled(False)
        self.mapViewsComboBox.currentIndexChanged.disconnect(self.select_map_view)
        self.mapViewsComboBox.clear()
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.mapViewsComboBox.setCurrentIndex(0)
        self.mapViewsComboBox.currentIndexChanged.connect(self.select_map_view)
        self.setMapViewPushButton.setEnabled(False)
        self.removeMapViewPushButton.setEnabled(False)
        self.updateFromMapViewPushButton.setEnabled(False)
        self.newFromMapViewPushButton.setEnabled(False)
        self.mapViewsComboBox.setEnabled(False)
        self.locationsGroupBox.setEnabled(False)
        self.processesGroupBox.setEnabled(False)
        self.processInformationGroupBox.setEnabled(False)
        return

    def select_role(self):
        self.addRoleToUserPushButton.setEnabled(False)
        self.removeRoleToUserPushButton.setEnabled(False)
        user_email = self.userComboBox.currentText()
        user_role = self.roleComboBox.currentText()
        if user_email in self.role_by_project_user:
            self.removeRoleToUserPushButton.setEnabled(True)
            self.addRoleToUserPushButton.setEnabled(False)
        else:
            self.removeRoleToUserPushButton.setEnabled(False)
            self.addRoleToUserPushButton.setEnabled(True)
        return

    def select_user(self):
        user_email = self.userComboBox.currentText()
        self.roleComboBox.currentIndexChanged.disconnect(self.select_role)
        self.roleComboBox.setCurrentIndex(0)
        self.roleComboBox.setEnabled(False)
        self.addRoleToUserPushButton.setEnabled(False)
        self.removeRoleToUserPushButton.setEnabled(False)
        self.roleComboBox.currentIndexChanged.connect(self.select_role)
        if user_email == defs_main.NO_COMBO_SELECT:
            return
        self.roleComboBox.setEnabled(True)
        if user_email in self.role_by_project_user:
            role = self.role_by_project_user[user_email]
            index = self.roleComboBox.findText(role)#, QtCore.Qt.MatchFixedString)
            if index != -1:
                self.roleComboBox.setCurrentIndex(index)
        return

    def set_map_view(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error, wkb_geometry = self.project.get_map_view_wkb_geometry(map_view_id)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        if not wkb_geometry:
            str_error = ('Null geometry for location: {}'.format(map_view_id))
            Tools.error_msg(str_error)
            self.update_locations()
            return
        str_error = self.qgis_iface.set_map_canvas_from_wkb_geometry_in_project_crs(wkb_geometry)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        return

    def set_qgis_iface(self, qgis_iface):
        self.qgis_iface = qgis_iface

    def update_map_view(self):
        if not self.qgis_iface:
            return
        map_view_id = self.mapViewsComboBox.currentText()
        if map_view_id == defs_main.NO_COMBO_SELECT:
            return
        str_error, wkb_geometry = self.qgis_iface.get_map_canvas_wkb_geometry_in_project_crs()
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        str_error = self.project.update_map_view(map_view_id, wkb_geometry)
        if str_error:
            Tools.error_msg(str_error)
            self.update_locations()
            return
        self.update_map_views()
        return

    def update_map_views(self):
        self.mapViewsComboBox.currentIndexChanged.disconnect(self.select_map_view)
        self.mapViewsComboBox.clear()
        self.mapViewsComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.mapViewsComboBox.setCurrentIndex(0)
        self.mapViewsComboBox.setEnabled(False)
        self.setMapViewPushButton.setEnabled(False)
        self.removeMapViewPushButton.setEnabled(False)
        self.updateFromMapViewPushButton.setEnabled(False)
        self.newFromMapViewPushButton.setEnabled(False)
        project_name = self.projectComboBox.currentText()
        if project_name == defs_main.NO_COMBO_SELECT:
            self.mapViewsComboBox.currentIndexChanged.connect(self.select_map_view)
            return
        str_error = self.project.load_map_views()
        map_views_names = self.project.get_map_views()
        map_views_names_to_add_as_list = []
        for map_view_name in map_views_names:
            map_views_names_to_add_as_list.append(map_view_name)
        map_views_names_to_add_as_list.sort()
        for map_view_name in map_views_names_to_add_as_list:
            self.mapViewsComboBox.addItem(map_view_name)
        self.mapViewsComboBox.currentIndexChanged.connect(self.select_map_view)
        self.mapViewsComboBox.setEnabled(True)
        self.locationsGroupBox.setEnabled(True)
        self.select_map_view()
        return

    def update_project_management(self):
        self.projectComboBox.currentIndexChanged.disconnect(self.select_project)
        self.projectComboBox.clear()
        self.projectComboBox.addItem(defs_main.NO_COMBO_SELECT)
        str_error, project_names = self.pgs_connection.get_project_names()
        if str_error:
            str_error = ('Error getting project names:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        if self.toolBox.isItemEnabled(0):
            project_names_to_add_as_list = []
            for project_name in project_names:
                project_names_to_add_as_list.append(project_name)
            project_names_to_add_as_list.sort()
            for project_name in project_names_to_add_as_list:
                self.projectComboBox.addItem(project_name)
        self.projectComboBox.currentIndexChanged.connect(self.select_project)
        self.select_project()
        return

    def update_user_management(self):
        self.role_by_project_user.clear()
        self.userComboBox.currentIndexChanged.disconnect(self.select_user)
        self.userComboBox.clear()
        self.userComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.userComboBox.setCurrentIndex(0)
        self.userComboBox.setEnabled(False)
        self.roleComboBox.setCurrentIndex(0)
        self.roleComboBox.setEnabled(False)
        self.addRoleToUserPushButton.setEnabled(False)
        self.removeRoleToUserPushButton.setEnabled(False)
        project_name = self.projectComboBox.currentText()
        if project_name == defs_main.NO_COMBO_SELECT:
            self.userComboBox.currentIndexChanged.connect(self.select_user)
            return
        str_error = self.pgs_connection.get_users()
        if str_error:
            str_error = ('Error getting users:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        project_users = self.project.db_project[defs_server_api.PROJECT_TAG_USERS]
        for project_user in project_users:
            project_user_id = project_user[defs_server_api.PROJECT_TAG_USERS_ID]
            if project_user_id == self.pgs_connection.user[defs_server_api.PROJECT_TAG_USERS_ID]:
                continue
            project_user_name = None
            project_user_email = None
            for user_email in self.pgs_connection.user_by_email:
                if self.pgs_connection.user_by_email[user_email][defs_server_api.PROJECT_TAG_USERS_ID] == project_user_id:
                    project_user_email = user_email
                    project_user_name = self.pgs_connection.user_by_email[user_email][defs_server_api.USERS_TAG_NAME]
                    break
            if not project_user_email is None:
                project_user_role = project_user[defs_server_api.PROJECT_TAG_USERS_ROLE]
                self.role_by_project_user[project_user_email] = project_user_role
        users_emails_to_add_as_list = []
        for db_user_email in self.pgs_connection.user_by_email:
            if db_user_email.casefold() == self.pgs_connection.user[defs_server_api.USERS_TAG_EMAIL].casefold():
                continue
            users_emails_to_add_as_list.append(db_user_email)
        users_emails_to_add_as_list.sort()
        userComboBoxModel = self.userComboBox.model()
        # item = self.combo.model().item(row)
        # item.setData(None, Qt.ForegroundRole)
        for db_user_email in users_emails_to_add_as_list:
            # if db_user_email.casefold() == self.pgs_connection.user[defs_server_api.USERS_TAG_EMAIL].casefold():
            #     continue
            if db_user_email in self.role_by_project_user:
                item = QStandardItem(db_user_email)
                item.setForeground(QColor('red'))
                # self.userComboBox.addItem(item)
                userComboBoxModel.appendRow(item)
            else:
                item = QStandardItem(db_user_email)
                item.setForeground(QColor('green'))
                # self.userComboBox.addItem(item)
                userComboBoxModel.appendRow(item)
            # item.setBackground(QBrush(QColorConstants.Red))
        self.userComboBox.currentIndexChanged.connect(self.select_user)
        self.userComboBox.setEnabled(True)
        self.select_user()
        return

    def update_qgis(self):
        if not self.qgis_iface:
            return
        # str_error = self.qgis_iface.update_all()
        # if str_error:
        #     str_error += ('Updating QGIS, error:\n{}'.format(str_error))
        #     Tools.error_msg(str_error)
        return
