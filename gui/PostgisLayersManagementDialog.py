# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import json
import copy
import pathlib

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
from PyQt5.QtGui import QStandardItemModel, QStandardItem

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
        self.layer_style_column = -1
        self.layer_name_column = -1
        self.initialize(title)

    def add_qgis_layers(self):
        layers_positions_to_process = []
        for row in range(self.tableWidget.rowCount()):
            item_layer_name = self.tableWidget.item(row, self.layer_name_column)
            if item_layer_name.checkState() == Qt.CheckState.Unchecked:
                continue
            layers_positions_to_process.append(row)
        if not layers_positions_to_process:
            msg = ('There are no selected layers.')
            QMessageBox.information(self, 'Information', msg)
            return

        return

    def delete_layers(self):
        layers_positions_to_process = []
        for row in range(self.tableWidget.rowCount()):
            item_layer_name = self.tableWidget.item(row, self.layer_name_column)
            if item_layer_name.checkState() == Qt.CheckState.Unchecked:
                continue
            layers_positions_to_process.append(row)
        if not layers_positions_to_process:
            msg = ('There are no selected layers.')
            QMessageBox.information(self, 'Information', msg)
            return
        target_file = self.targetFileLineEdit.text()
        if not target_file:
            msg = ('Select target file before.')
            QMessageBox.information(self, 'Information', msg)
            return

        return

    def download_layers(self):
        layers_positions_to_process = []
        for row in range(self.tableWidget.rowCount()):
            item_layer_name = self.tableWidget.item(row, self.layer_name_column)
            if item_layer_name.checkState() == Qt.CheckState.Unchecked:
                continue
            layers_positions_to_process.append(row)
        if not layers_positions_to_process:
            msg = ('There are no selected layers.')
            QMessageBox.information(self, 'Information', msg)
            return

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
        self.tableWidget.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        return

    def on_click(self, item):
        row = item.row()
        col = item.column()
        str_value = item.text()
        label = self.tableWidget.horizontalHeaderItem(col).text()
        if col == self.layer_name_column:
            currentState = item.checkState()
            return
        item_layer_name = self.tableWidget.item(row, self.layer_name_column)
        if item_layer_name.checkState() == Qt.CheckState.Unchecked:
            return
        layer = self.project.pgs_connection.layers[row]
        if col == self.layer_style_column:
            layer_name = self.tableWidget.item(row, self.layer_name_column).text()
            layer_styles = layer[defs_server_api.LAYER_TAG_STYLES]
            if not layer_styles: # there are no styles
                return
            layer_styles.insert(0, defs_pglm.NO_STYLE)
            current_pos = layer_styles.index(str_value)
            title = defs_pglm.TITLE_SELECT_LAYER_STYLE
            selected_value, ok = QInputDialog.getItem(self, title, defs_pglm.STYLE_LABEL, layer_styles, current_pos, False)
            if ok:# and item:
                self.tableWidget.item(row, col).setText(selected_value)
            return
        return

    def remove_qgis_layers(self):
        layers_positions_to_process = []
        for row in range(self.tableWidget.rowCount()):
            item_layer_name = self.tableWidget.item(row, self.layer_name_column)
            if item_layer_name.checkState() == Qt.CheckState.Unchecked:
                continue
            layers_positions_to_process.append(row)
        if not layers_positions_to_process:
            msg = ('There are no selected layers.')
            QMessageBox.information(self, 'Information', msg)
            return

        return

    def select_target_file(self):
        title = "Select download target file"
        previous_file = self.targetFileLineEdit.text()
        last_path = self.project.settings.value("last_path")
        if not last_path:
            last_path = QDir.currentPath()
            self.project.settings.setValue("last_path", last_path)
            self.project.settings.sync()
        dlg = QFileDialog()
        dlg.setDirectory(last_path)
        dlg.setFileMode(QFileDialog.AnyFile)
        dlg.setNameFilter("Download target file (*.gpkg)")
        if dlg.exec_():
            file_names = dlg.selectedFiles()
            file_name = file_names[0]
        else:
            return
        if file_name:
            if pathlib.Path(file_name).suffix != '.gpkg':
                file_name = file_name + '.gpkg'
            self.targetFileLineEdit.setText(file_name)
            last_path = QFileInfo(file_name).absolutePath()
            self.project.settings.setValue("last_path", last_path)
            self.project.settings.sync()
        return

    def update_gui(self, update_from_postgis = True):
        if update_from_postgis:
            str_error = self.update_postgis_layers()
            if str_error:
                self.accept()
        self.layer_style_column = -1
        self.layer_name_column = -1
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
                    if self.layer_style_column == -1:
                        self.layer_style_column = j
                pg_field_label =defs_pglm.layer_pg_field_label[field_label]
                field_value = layer[pg_field_label]
                item = QTableWidgetItem(field_value)
                item.setTextAlignment(Qt.AlignCenter)
                if pg_field_label == defs_server_api.LAYER_TAG_TABLE_NAME:
                    if self.layer_name_column == -1:
                        self.layer_name_column = j
                    item.setCheckState(QtCore.Qt.Unchecked)
                    # item.setCheckState(QtCore.Qt.Checked)
                    currentState = item.checkState()
                    item.setData(QtCore.Qt.UserRole, currentState)
                self.tableWidget.setItem(rowPosition, j, item)
            # if no style set text to NO_STYLE
            if self.layer_style_column != -1:
                if not self.tableWidget.item(rowPosition, self.layer_style_column).text():
                    self.tableWidget.item(rowPosition, self.layer_style_column).setText(defs_pglm.NO_STYLE)
        self.tableWidget.resizeColumnsToContents()
        return

    def update_layers_from_postgis(self):
        str_error = ''
        project_id = self.project.db_project[defs_server_api.PROJECT_TAG_ID]
        # db_schema = defs_server_api.PROJECT_SCHEMA_PREFIX + str(project_id)
        str_error = self.project.pgs_connection.get_layers(project_id)
        return str_error

    def update_postgis_layers(self):
        layers_positions_to_process = []
        for row in range(self.tableWidget.rowCount()):
            item_layer_name = self.tableWidget.item(row, self.layer_name_column)
            if item_layer_name.checkState() == Qt.CheckState.Unchecked:
                continue
            layers_positions_to_process.append(row)
        if not layers_positions_to_process:
            msg = ('There are no selected layers.')
            QMessageBox.information(self, 'Information', msg)
            return

        return
