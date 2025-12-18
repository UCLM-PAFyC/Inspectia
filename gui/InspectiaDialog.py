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
        process_path_by_provider = {}
        for provider in app_defs_processes.processes_providers:
            process_path_by_provider[provider] = []
            process_path_by_provider[provider].append(app_defs_processes.processes_path)
        for provider in postgis_api_defs_processes.processes_providers:
            if not provider in process_path_by_provider:
                process_path_by_provider[provider] = []
            process_path_by_provider[provider].append(postgis_api_defs_processes.processes_path)
        processes_manager = ProcessesManager()
        str_error = processes_manager.initialize(process_path_by_provider)
        if str_error:
            Tools.error_msg(str_error)
            return
        self.processes_manager = processes_manager
        self.processesManagerPushButton.clicked.connect(self.select_processes_manager_gui)
        self.toolBox.setEnabled(False)
        # self.toolBox.setItemEnabled(0, False)
        # self.toolBox.setItemEnabled(1, False)
        # if self.qgis_iface is None:
        #     self.locationsGroupBox.setEnabled(False)
        # return

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
