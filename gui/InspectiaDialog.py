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

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from Inspectia.defs import defs_paths
from Inspectia.defs import defs_main
from Inspectia.defs import defs_qsettings

common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
sys.path.append(common_libs_absolute_path)

from Inspectia.lib.ProjectInspectia import ProjectInspectia

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibProcesses.defs import defs_processes
# from pyLibProcesses.defs import defs_project as processes_defs_project
# from pyLibProcesses.ProcessesManager import ProcessesManager
# from pyLibProcesses.gui.ProcessesManagerDialog import ProcessesManagerDialog
# from pyLibProcesses.gui.ProjectProcessesDialog import ProjectProcessesDialog
from pyLibQtTools import Tools
from pyLibQtTools.LoginDialog import LoginDialog
from pyLibGisApi.lib.PostGISServerAPI import PostGISServerConnection
from pyLibGisApi.defs import defs_server_api


# from pyLibQtTools.Tools import SimpleTextEditDialog
# from pyLibParameters import defs_pars
# from pyLibParameters.ParametersManager import ParametersManager
# from pyLibParameters.ui_qt.ParametersManagerDialog import ParametersManagerDialog
# from pyLibQtTools.QProcessDialog import QProcessDialog
# from pyLibQtTools import defs_qprocess
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
        self.initialize()

    def close_project(self):
        self.projectDefinitionPushButton.setEnabled(False)
        self.openProjectPushButton.setEnabled(True)
        self.closeProjectPushButton.setEnabled(False)
        self.deleteProjectPushButton.setEnabled(True)
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
        self.update_project_management_page()
        return

    def initialize(self):
        self.crs_tools = CRSsTools()
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
        self.projectComboBox.addItem(defs_main.NO_COMBO_SELECT)
        self.projectRolLineEdit.setEnabled(False)
        self.projectComboBox.currentIndexChanged.connect(self.select_project)
        self.closeProjectPushButton.clicked.connect(self.close_project)
        self.deleteProjectPushButton.clicked.connect(self.delete_project)
        self.newProjectPushButton.clicked.connect(self.new_project)
        self.openProjectPushButton.clicked.connect(self.open_project)
        self.projectDefinitionPushButton.clicked.connect(self.project_definition)
        # process_path_by_provider = {}
        # for provider in app_defs_processes.processes_providers:
        # process_path_by_provider[provider] = []
        # process_path_by_provider[provider].append(app_defs_processes.processes_path)
        # for provider in photogrammetry_defs_processes.processes_providers:
        # if not provider in process_path_by_provider:
        # process_path_by_provider[provider] = []
        # process_path_by_provider[provider].append(photogrammetry_defs_processes.processes_path)
        # processes_manager = ProcessesManager()
        # str_error = processes_manager.initialize(process_path_by_provider)
        # if str_error:
        # Tools.error_msg(str_error)
        # return
        # self.processes_manager = processes_manager
        # self.processesManagerPushButton.clicked.connect(self.select_processes_manager_gui)
        self.toolBox.setItemEnabled(0, False)
        self.toolBox.setItemEnabled(1, False)
        return

    def login(self):
        self.projectComboBox.setCurrentIndex(0)
        self.toolBox.setItemEnabled(0, False)
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
                self.update_project_management_page()
            return
        email = dialog.email
        password = dialog.password
        url = dialog.url
        str_error = self.pgs_connection.login(url, email, password)
        # str_error = self.project.login(url, username, password)
        if str_error:
            str_error = ('Error logging:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            if self.gis_server_api_email is None:
                self.toolBox.setItemEnabled(0, False)
                # self.update_project_management_page()
            return
        self.gis_server_api_url = url
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_URL, self.gis_server_api_url)
        self.gis_server_api_email = email
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_EMAIL, self.gis_server_api_email)
        self.gis_server_api_password = password
        self.settings.setValue(defs_qsettings.QSETTINGS_TAG_GIS_SERVER_API_PASSWORD, self.gis_server_api_password)
        self.settings.sync()
        self.toolBox.setItemEnabled(0, True)
        self.update_project_management_page()
        self.toolBox.setCurrentIndex(0)
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
        self.update_project_management_page()
        return

    def open_project(self):
        self.projectDefinitionPushButton.setEnabled(False)
        self.openProjectPushButton.setEnabled(True)
        self.closeProjectPushButton.setEnabled(False)
        self.deleteProjectPushButton.setEnabled(True)
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
        self.projectDefinitionPushButton.setEnabled(True)
        self.openProjectPushButton.setEnabled(False)
        self.closeProjectPushButton.setEnabled(True)
        self.deleteProjectPushButton.setEnabled(False)
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

    def select_project(self):
        self.user_is_owner = False
        self.user_is_admin = False
        self.user_is_editor = False
        self.user_is_user = False
        project_name = self.projectComboBox.currentText()
        if project_name == defs_main.NO_COMBO_SELECT:
            self.openProjectPushButton.setEnabled(False)
            self.closeProjectPushButton.setEnabled(False)
            self.newProjectPushButton.setEnabled(True)
            self.deleteProjectPushButton.setEnabled(False)
            self.projectRolLineEdit.setEnabled(False)
            self.projectDefinitionPushButton.setEnabled(False)
        else:
            str_error, project_role = self.pgs_connection.get_project_role_by_name(project_name)
            if str_error:
                str_error = ('Getting role for project: {}, error:\n{}'.format(project_name, str_error))
                Tools.error_msg(str_error)
                self.projectComboBox.setCurrentIndex(0)
                return
            self.projectRolLineEdit.setEnabled(True)
            self.openProjectPushButton.setEnabled(True)
            self.closeProjectPushButton.setEnabled(False)
            self.newProjectPushButton.setEnabled(False)
            if project_role.casefold() == defs_server_api.ROL_OWNER.casefold():
                self.user_is_owner = True
            elif project_role.casefold() == defs_server_api.ROL_ADMIN.casefold():
                self.user_is_admin = True
            elif project_role.casefold() == defs_server_api.ROL_EDITOR.casefold():
                self.user_is_editor = True
            elif project_role.casefold() == defs_server_api.ROL_USER.casefold():
                self.user_is_user = True
            if self.user_is_owner:
                self.deleteProjectPushButton.setEnabled(True)
            self.projectRolLineEdit.setText(project_role)
            self.projectDefinitionPushButton.setEnabled(False)
            if self.user_is_owner:
                self.deleteProjectPushButton.setEnabled(True)
            else:
                self.deleteProjectPushButton.setEnabled(False)
        return

    def set_qgis_iface(self, qgis_iface):
        self.qgis_iface = qgis_iface

    def update_project_management_page(self):
        self.projectComboBox.currentIndexChanged.disconnect(self.select_project)
        self.projectComboBox.clear()
        self.projectComboBox.addItem(defs_main.NO_COMBO_SELECT)
        str_error, project_names = self.pgs_connection.get_project_names()
        if str_error:
            str_error = ('Error getting project names:\n{}'.format(str_error))
            Tools.error_msg(str_error)
            return
        if self.toolBox.isItemEnabled(0):
            for project_name in project_names:
                self.projectComboBox.addItem(project_name)
        self.projectComboBox.currentIndexChanged.connect(self.select_project)
        self.select_project()
        return

    def update_qgis(self):
        if not self.qgis_iface:
            return
        # str_error = self.qgis_iface.update_all()
        # if str_error:
        #     str_error += ('Updating QGIS, error:\n{}'.format(str_error))
        #     Tools.error_msg(str_error)
        return
