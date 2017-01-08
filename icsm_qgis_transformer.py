# -*- coding: utf-8 -*-
"""
/***************************************************************************
 icsm_ntv2_transformer
                                 A QGIS plugin
 This plugin uses official ICSM grids to transform between Australian coordinate systems.
                              -------------------
        begin                : 2017-01-08
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Alex Leith
        email                : alex@auspatious.com
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
import os.path

import resources
from icsm_qgis_transformer_dialog import icsm_ntv2_transformerDialog
from PyQt4.QtCore import (SIGNAL, QCoreApplication, QObject, QSettings,
                          QTranslator, qVersion)
from PyQt4.QtGui import QAction, QFileDialog, QIcon
from qgis.core import (QgsMessageLog, QgsRasterLayer, QgsVectorLayer,
    QgsCoordinateReferenceSystem, QgsRasterPipe, QgsRasterFileWriter, QgsCoordinateTransform)
from qgis.gui import QgsMessageBar


def log(message, error=False):
    log_level = QgsMessageLog.INFO
    if error:
        log_level = QgsMessageLog.CRITICAL
    QgsMessageLog.logMessage(message, 'ICSM NTv2 Transformer', )


class icsm_ntv2_transformer:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface

        dir(icsm_ntv2_transformerDialog)

        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'icsm_ntv2_transformer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ICSM NTv2 Transformer')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'icsm_ntv2_transformer')
        self.toolbar.setObjectName(u'icsm_ntv2_transformer')

        self.in_file = None
        self.out_file = None
        # This is structured as in OriginProjString, OriginEPSG, NewProjString, NewEPSG
        self.transformations = {
            'AGD66 to GDA94': [
                '+proj=utm +zone=<ZONE> +south +ellps=aust_SA +towgs84=-117.808,-51.536,137.784,0.303,0.446,0.234,-0.29 +units=m +no_defs +nadgrids=' + os.path.dirname(__file__) + '/grids/A66_National.gsb +wktext',
                '202',
                None,
                '283'
            ],
            'AGD84 to GDA94': [
                '+proj=utm +zone=<ZONE> +south +ellps=aust_SA +towgs84=-134,-48,149,0,0,0,0 +units=m +no_defs +nadgrids=' + os.path.dirname(__file__) + '/grids/A84_National.gsb +wktext',
                '203',
                None,
                '283'
            ]
        }

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
        return QCoreApplication.translate('icsm_ntv2_transformer', message)

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
        parent=None
    ):
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

        # Create the dialog (after translation) and keep reference
        self.dlg = icsm_ntv2_transformerDialog()

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

        icon_path = ':/plugins/icsm_ntv2_transformer/icon.png'
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'ICSM NTv2 Transformer'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&ICSM NTv2 Transformer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def browse_infiles(self):
        newname = QFileDialog.getOpenFileName(
            None, "Input File", self.dlg.in_file_name.displayText(), "Any supported filetype (*.*)")

        if newname:
            self.dlg.in_file_name.setText(newname)

    def browse_outfiles(self):
        newname = QFileDialog.getSaveFileName(
            None, "Output file", self.dlg.out_file_name.displayText(), "Shapefile or TIFF (*.shp, *.tiff)")

        if newname:
            self.dlg.out_file_name.setText(newname)

    def get_epsg(self, layer):
        return layer.crs().authid().split(':')[1]

    def transform_vector(self, layer, transform):
        qgis.core.QgsVectorFileWriter.writeAsVectorFormat(layer, out_file, 'utf-8', dest_crs, 'Shapefile')

        pass

    def get_orig_dest_crs(self, transform, zone, string=False):
        transformation_parameters = self.transformations[transform]
        orig_proj = transformation_parameters[0]
        orig_epsg = transformation_parameters[1] + zone
        orig_string = ""

        dest_proj = transformation_parameters[2]
        dest_epsg = transformation_parameters[3] + zone
        dest_string = ""

        if orig_proj is not None:
            log("using proj for orig")
            orig_string = orig_proj.replace('<ZONE>', zone)
            orig_crs = QgsCoordinateReferenceSystem()
            orig_crs.createFromProj4(orig_string)
        else:
            log("using epsg for orig")
            orig_crs = QgsCoordinateReferenceSystem(int(orig_epsg), QgsCoordinateReferenceSystem.PostgisCrsId)
            orig_string = "EPSG:" + orig_epsg

        if dest_proj is not None:
            log("using proj for dest")
            dest_string = dest_proj.replace('<ZONE>', zone)
            dest_crs = QgsCoordinateReferenceSystem()
            dest_crs.createFromProj4(dest_string)
        else:
            log("using epsg for dest")
            dest_crs = QgsCoordinateReferenceSystem(int(dest_epsg), QgsCoordinateReferenceSystem.PostgisCrsId)
            orig_string = "EPSG:" + orig_epsg

        if string:
            return orig_string, dest_string
        else:
            return orig_crs, dest_crs

    def transform_raster(self, layer, transform, out_file):
        epsg = self.get_epsg(layer)
        transform_params = self.transformations[transform]
        if transform_params[1] != epsg[0:3]:
            log("Origin EPSG ({}) doesn't match transform {}, check you're using the right transform.".format(epsg, transform_params[1] + 'XX'))
            return None

        zone = epsg[3:]

        orig_crs, dest_crs = self.get_orig_dest_crs(transform, zone)

        layer.setCrs(orig_crs)
        tr = QgsCoordinateTransform(orig_crs, dest_crs)

        file_writer = QgsRasterFileWriter(out_file)
        pipe = QgsRasterPipe()
        provider = layer.dataProvider()
        pipe.set(provider.clone())
        result = file_writer.writeRaster(
            pipe,
            provider.xSize(),
            provider.ySize(),
            tr.transform(provider.extent()),
            dest_crs
        )
        log(str(result))

    def run(self):
        """Run method that performs all the real work"""

        QObject.connect(self.dlg.in_file_browse, SIGNAL("clicked()"), self.browse_infiles)
        QObject.connect(self.dlg.out_file_browse, SIGNAL("clicked()"), self.browse_outfiles)

        self.dlg.transformation_picker.addItems(self.transformations.keys())

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            log("Starting transform process...")
            in_file = self.dlg.in_file_name.text()
            out_file = self.dlg.out_file_name.text()

            if out_file is None:
                log("No outfile set, writing to default name.")

            transform = self.dlg.transformation_picker.currentText()

            log(str(transform))

            fail = False
            is_vector = True

            layer = QgsVectorLayer(in_file, 'in layer', 'ogr')
            if not layer.isValid():
                print("Layer failed to load! Trying raster")
                layer = QgsRasterLayer(in_file, 'in layer')
                if not layer.isValid():
                    print "Layer failed to load!"
                    fail = True
                else:
                    # We have a raster!
                    is_vector = False
            if not fail:
                if is_vector:
                    log("Found a valid vector layer.")
                    self.transform_vector(layer, transform, out_file)
                else:
                    log("Found a valid raster layer.")
                    self.transform_raster(layer, transform, out_file)
            else:
                log("Couldn't load file {} as a vector or raster".format(in_file), True)
                self.iface.messageBar().pushMessage("Error", "Couldn't load in file as vector or raster", level=QgsMessageBar.CRITICAL, duration=3)
