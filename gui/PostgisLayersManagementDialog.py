# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import json
import copy

current_path = os.path.dirname(os.path.realpath(__file__))
# current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from PyQt5 import QtCore, QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QInputDialog, QHBoxLayout, QDoubleSpinBox,
                             QFileDialog, QPushButton, QComboBox, QPlainTextEdit, QLineEdit, QDateEdit,
                             QDialogButtonBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QAbstractItemView)
from PyQt5.QtCore import QDir, QFileInfo, QFile, QSize, Qt, QDate
from PyQt5.QtGui import QStandardItemModel

from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog
from pyLibQtTools.CalendarDialog import CalendarDialog
from pyLibProject.defs import defs_project_definition
from pyLibGisApi.defs import defs_server_api
from Inspectia.defs import defs_pgLayersManagement as defs_pglm
from pyLibGisApi.defs import defs_server_api

class PostgisLayersManagementDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 project,
                 title,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'PostgisLayersManagementDialog.ui'), self)
        self.project = project
        self.last_path = None
        self.title = title
        self.str_error = ""
        self.use_layer_style_column = -1
        self.initialize(title)

    def add_qgis_layers(self):
        return

    def delete_layers(self):
        return

    def download_layers(self):
        return

    def get_error(self):
        return self.str_error

    def initialize(self, title):
        self.setWindowTitle(title)
        self.str_error = self.update_layers_from_postgis();
        if self.str_error:
            return
        if not self.project.pgs_connection.layers:
            self.str_error = "There are no PostGIS layers"
            return
        fields_labels = defs_pglm.field_labels
        self.tableWidget.setColumnCount(len(fields_labels))
        self.tableWidget.setStyleSheet("QHeaderView::section { color:black; background : lightGray; }")
        for i in range(len(fields_labels)):
            field_label = fields_labels[i]
            header_item = QTableWidgetItem(field_label)
            # header_tooltip = parameter[defs_pars.PARAMETER_FIELD_DESCRIPTION]
            # header_item.setToolTip(header_tooltip)
            self.tableWidget.setHorizontalHeaderItem(i, header_item)
        self.tableWidget.setSortingEnabled(True)
        self.tableWidget.itemDoubleClicked.connect(self.on_click)
        self.tableWidget.itemClicked.connect(self.on_click)
        self.targetFilePushButton.clicked.connect(self.select_target_file)
        self.downloadPushButton.clicked.connect(self.download_layers)
        self.deletePushButton.clicked.connect(self.delete_layers)
        self.updateStylePushButton.clicked.connect(self.update_postgis_layers)
        self.addQgisPushButton.clicked.connect(self.add_qgis_layers)
        self.removeQgisPushButton.clicked.connect(self.remove_qgis_layers)
        self.update_gui(update_from_postgis=False)
        return

    def on_click(self):
        return

    def remove_qgis_layers(self):
        return

    def select_target_file(self):
        return

    def update_gui(self, update_from_postgis = True):
        if update_from_postgis:
            str_error = self.update_postgis_layers()
            if str_error:
                self.accept()
        self.use_layer_style_column = -1
        self.tableWidget.setRowCount(0)
        layers = self.project.pgs_connection.layers
        style_column = -1
        for i in range(len(layers)):
            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)
            layer = layers[i]
            for j in range(len(defs_pglm.field_labels)):
                field_label = defs_pglm.field_labels[j]
                if field_label == defs_pglm.STYLE_LABEL:
                    if self.use_layer_style_column == -1:
                        self.use_layer_style_column = j
                pg_field_label =defs_pglm.layer_pg_field_label[field_label]
                field_value = layer[pg_field_label]
                item = QTableWidgetItem(field_value)
                item.setTextAlignment(Qt.AlignCenter)
                if j == 0:
                    item.setCheckState(QtCore.Qt.Unchecked)
                    # item.setCheckState(QtCore.Qt.Checked)
                    currentState = item.checkState()
                    item.setData(QtCore.Qt.UserRole, currentState)
                self.tableWidget.setItem(rowPosition, j, item)
        return

    def update_layers_from_postgis(self):
        str_error = ''
        project_id = self.project.db_project[defs_server_api.PROJECT_TAG_ID]
        # db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error = self.project.pgs_connection.get_layers(project_id)
        return str_error

    def update_postgis_layers(self):
        return
