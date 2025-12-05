# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name			 	 : qInspectia
Description          : Q QGIS plugin to ...
Date                 : October/2025
copyright            : (C) David Hernandez Lopez
email                : david.hernandez@uclm.es
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
# Initialize Qt resources from file resources.py
# from .resources import *
# from .resources_rc import *

import os.path
import sys
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QTabWidget, QInputDialog, QLineEdit
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QFileInfo, QDir, QObject, QFile
from qgis.core import QgsApplication, QgsDataSourceUri, Qgis

strQGISVersion = Qgis.QGIS_VERSION
versionItems = strQGISVersion.split('.')
qGisFirstVersion = int(versionItems[0])
qGisSecondVersion = int(versionItems[1])
strThirdVersion = versionItems[2]
strThirdVersionItems = strThirdVersion.split('-')
qGisThirdVersion = int(strThirdVersionItems[0])
from osgeo import osr

projVersionMajor = osr.GetPROJVersionMajor()
# projVersionMinor = osr.GetPROJVersionMinor()
pluginsPath = QFileInfo(QgsApplication.qgisUserDatabaseFilePath()).path()
pluginPath = os.path.dirname(os.path.realpath(__file__))
pluginPath = os.path.join(pluginsPath, pluginPath)
libPath = os.path.join(pluginPath, 'lib')
# existsPluginPath = QDir(libPath).exists()
sys.path.append(pluginPath)
sys.path.append(libPath)
current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

# Import the code for the dialog
from Inspectia.gui.InspectiaDialog import InspectiaDialog
from Inspectia.defs import defs_main
from Inspectia.lib.QGisIFaceInspectia import QGisIFaceInspectia

# # sys.path.append("C:\Program Files\JetBrains\PyCharm 2020.3\debug-eggs\pydevd-pycharm.egg") # dhl
# sys.path.append("C:\Program Files\JetBrains\PyCharm 2023.2\debug-eggs\pydevd-pycharm.egg")  # dhl
# sys.path.append("C:\Program Files\JetBrains\PyCharm 2023.2\debug-eggs\pydevd-pycharm.egg")  # dhl
# sys.path.append("C:\\Program Files\\JetBrains\\PyCharm 2025.2.0.1\\debug-eggs\\pydevd-pycharm.egg")  # dhl
# import pydevd_pycharm
# import pydevd

class qInspectia(object):

    def __init__(self, iface):

        # pydevd.settrace('localhost', port=54100)
        # # pydevd_pycharm.settrace('localhost', port=54100, stdout_to_server=True, stderr_to_server=True)

        self.projVersionMajor = projVersionMajor
        self.path_plugin = pluginPath
        self.path_lib = libPath
        self.plugin_dir = os.path.dirname(__file__)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'qInspectia{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        path_file_qsettings = self.plugin_dir + "/" + defs_main.SETTINGS_FILE
        self.plugin_settings = QSettings(path_file_qsettings, QSettings.IniFormat)
        self.actions = []
        self.menu = self.tr(u'&qInspectia')
        self.toolbar = self.iface.addToolBar(u'qInspectia')
        self.toolbar.setObjectName(u'qInspectia')
        self.pluginIsActive = False
        self.widget = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('qInspectia', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = pluginPath + "/" + defs_main.IMAGES_PATH + "/" + defs_main.LOGO_ICON_FILE
        self.add_action(
            icon_path,
            text=self.tr(u'qInspectia'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        # disconnects
        self.widget.finished.disconnect(self.onClosePlugin)

        # remove this statement if dockwidget is to remain
        # for reuse if plugin is reopened
        # Commented next statement since it causes QGIS crashe
        # when closing the docked window:
        # self.dockwidget = None

        self.pluginIsActive = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&qInspectia'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        if self.pluginIsActive:
            return
        self.pluginIsActive = True
        if self.widget == None:
            # self.widget = qAicedroneDockWidget(self.iface)
            self.widget = InspectiaDialog(self.plugin_settings, pluginPath)
            qgis_iface = QGisIFaceInspectia(self.iface, self.path_plugin)
            self.widget.set_qgis_iface(qgis_iface)
        self.widget.finished.connect(self.onClosePlugin)
        # self.widget.closingPlugin.connect(self.onClosePlugin)
        # self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
        self.widget.show()
        self.iface.mainWindow().showMaximized()
        self.iface.mainWindow().update()







