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
from __future__ import print_function

import os.path
import subprocess

from gdalconst import GA_ReadOnly
from osgeo import gdal, osr

from icsm_qgis_transformer_dialog import icsm_ntv2_transformerDialog
from PyQt4.QtCore import (SIGNAL, QCoreApplication, QObject, QSettings,
                          QTranslator, qVersion)
from PyQt4.QtGui import QAction, QFileDialog, QIcon
from qgis.core import (QgsCoordinateReferenceSystem, QgsMessageLog,
                       QgsVectorFileWriter, QgsVectorLayer)
from qgis.gui import QgsMessageBar


def log(message, error=False):
    log_level = QgsMessageLog.INFO
    if error:
        log_level = QgsMessageLog.CRITICAL
    QgsMessageLog.logMessage(message, 'ICSM NTv2 Transformer', level=log_level)


class icsm_ntv2_transformer:
    """QGIS Plugin Implementation."""
    AGD66GRID = os.path.dirname(__file__) + '/grids/A66_National_13_09_01.gsb'
    AGD84GRID = os.path.dirname(__file__) + '/grids/National_84_02_07_01.gsb'

    SUPPORTED_EPSG = {
        'EPSG:20249': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 49],
        'EPSG:20250': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 50],
        'EPSG:20251': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 51],
        'EPSG:20252': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 52],
        'EPSG:20253': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 53],
        'EPSG:20254': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 54],
        'EPSG:20255': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 55],
        'EPSG:20256': ["AGD66 to GDA94", 'AGD66 AMG [EPSG:202XX]', 'GDA94 MGA [EPSG:283XX]', 56],
        'EPSG:20349': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 49],
        'EPSG:20350': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 50],
        'EPSG:20351': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 51],
        'EPSG:20352': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 52],
        'EPSG:20353': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 53],
        'EPSG:20354': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 54],
        'EPSG:20355': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 55],
        'EPSG:20356': ["AGD84 to GDA94", 'AGD84 AMG [EPSG:203XX]', 'GDA94 MGA [EPSG:283XX]', 56],
        'EPSG:4202': ["AGD66 to GDA94", 'AGD66 LonLat [EPSG:4202]', 'GDA94 LonLat [EPSG:4283]', False],
        'EPSG:4203': ["AGD66 to GDA94", 'AGD84 LonLat [EPSG:4203]', 'GDA94 LonLat [EPSG:4283]', False]
    }

    TRANSFORMATIONS = {
        "AGD66 to GDA94": '',
        "AGD84 to GDA94": '',
        "GDA94 to AGD66": '',
        "GDA94 to AGD84": '',
    }

    CRS_STRINGS = {
        'AGD66 AMG [EPSG:202XX]': [
            'EPSG:202{zone}',
            '+proj=utm +zone={zone} +south +ellps=aust_SA +units=m +no_defs +nadgrids=' + AGD66GRID + ' +wktext',
        ],
        'AGD84 AMG [EPSG:203XX]': [
            'EPSG:203{zone}',
            '+proj=utm +zone={zone} +south +ellps=aust_SA +units=m +no_defs +nadgrids=' + AGD84GRID + ' +wktext',
        ],
        'AGD66 LonLat [EPSG:4202]': [
            'EPSG:4202',
            '+proj=longlat +ellps=aust_SA +no_defs +nadgrids=' + AGD66GRID + ' +wktext',
        ],
        'AGD84 LonLat [EPSG:4203]': [
            'EPSG:4203',
            '+proj=longlat +ellps=aust_SA +no_defs +nadgrids=' + AGD84GRID + ' +wktext'
        ],
        'GDA94 MGA [EPSG:283XX]': [
            'EPSG:283{zone}',
            None
        ],
        'GDA94 LonLat [EPSG:4283]': [
            'EPSG:4238',
            None
        ]
    }

    def __init__(self, iface):
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
        self.toolbar = self.iface.addToolBar(u'icsm_ntv2_transformer')
        self.toolbar.setObjectName(u'icsm_ntv2_transformer')

        self.in_file = None
        self.out_file = None

        self.in_dataset = None

        self.in_file_type = None

        self.in_file_crs = None
        self.out_file_crs = None

        self.in_file_proj_string = None

        self.oldValidation = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
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

    def update_transform_text(self, text):
        self.dlg.transform_text.setPlainText(text)

    def transform_changed(self):
        self.validate_source_transform()

    def get_dest_crs(self, source_crs):
        this_source_crs = self.SUPPORTED_EPSG[self.in_file_crs]

        dest_crs = self.CRS_STRINGS[this_source_crs[2]][0]
        zone = this_source_crs[3]

        if zone:
            dest_crs = dest_crs.format(zone=zone)

        return dest_crs

    def get_source_proj_string(self, source_crs):
        this_source_crs = self.SUPPORTED_EPSG[self.in_file_crs]

        proj_string = self.CRS_STRINGS[this_source_crs[1]][1]
        zone = this_source_crs[3]

        if zone:
            proj_string = proj_string.format(zone=zone)

        return proj_string

    def validate_source_transform(self):
        if not self.in_file and not self.in_file_type and not self.in_file_crs:
            self.update_transform_text("Select an input file.")
            return
        transform = self.dlg.transformation_picker.currentText()
        if self.in_file_crs in self.SUPPORTED_EPSG:
            log("Selected CRS is supported")
            this_source_crs = self.SUPPORTED_EPSG[self.in_file_crs]
            if this_source_crs[0] == transform:
                log("We've got a valid transform for this CRS")
                self.out_file_crs = self.get_dest_crs(self.in_file_crs)
                self.in_file_proj_string = self.get_source_proj_string(self.in_file_crs)
                log("Using source proj string: {}".format(self.in_file_proj_string))
                self.update_transform_text("Source CRS is {}\nDestination CRS is {}\nUsing accurate grid transform from {}".format(
                    self.in_file_crs, self.out_file_crs, self.dlg.transformation_picker.currentText()))
            else:
                log("No valid transform for this CRS")
                self.in_file_type = None
                self.update_transform_text("Transformation {} is not valid for the input file's CRS {}".format(transform, self.in_file_crs))
        else:
            log("Selected CRS is NOT supported.")
            self.in_file_type = None
            self.update_transform_text("The CRS {} for the selected input file is not supported.".format(self.in_file_crs))

    def browse_infiles(self):
        newname = QFileDialog.getOpenFileName(
            None, "Input File", self.dlg.in_file_name.displayText(), "Any supported filetype (*.*)")

        if newname:
            self.in_file_type = None
            fail = False
            layer = QgsVectorLayer(newname, 'in layer', 'ogr')
            if layer.isValid():
                self.in_file_type = 'VECTOR'
                self.in_file_crs = layer.crs().authid()
                self.validate_source_transform()
                self.in_dataset = layer
            else:
                dataset = gdal.Open(newname, GA_ReadOnly)
                if dataset is None:
                    fail = True
                else:
                    # We have a raster!
                    self.in_file_type = 'RASTER'
                    prj = dataset.GetProjection()
                    crs = QgsCoordinateReferenceSystem(prj)
                    self.in_file_crs = crs.authid()
                    self.validate_source_transform()
                    self.in_dataset = dataset
            if fail:
                self.iface.messageBar().pushMessage(
                    "Error", "Couldn't read 'in file' {} as vector or raster".format(newname), level=QgsMessageBar.CRITICAL, duration=3)

            self.dlg.in_file_name.setText(newname)

    def browse_outfiles(self):
        newname = QFileDialog.getSaveFileName(
            None, "Output file", self.dlg.out_file_name.displayText(), "Shapefile or TIFF (*.shp, *.tiff)")

        if newname:
            self.dlg.out_file_name.setText(newname)

    def get_epsg(self, layer):
        return layer.crs().authid().split(':')[1]

    def transform_vector(self, out_file):
        layer = self.in_dataset

        source_crs = QgsCoordinateReferenceSystem()
        source_crs.createFromProj4(self.in_file_proj_string)

        layer.setCrs(source_crs)

        dest_crs = QgsCoordinateReferenceSystem()
        dest_crs.createFromId(int(self.out_file_crs.split(':')[1]))

        error = QgsVectorFileWriter.writeAsVectorFormat(layer, out_file, 'utf-8', dest_crs, 'ESRI Shapefile')
        if error == QgsVectorFileWriter.NoError:
            log("Success")
            self.iface.messageBar().pushMessage(
                "Success", "Transformation complete.", level=QgsMessageBar.INFO, duration=3)
        else:
            log("Error writing vector, code: {}".format(str(error)))
            self.iface.messageBar().pushMessage(
                "Error", "Transformation failed, please check your configuration.", level=QgsMessageBar.CRITICAL, duration=3)

    def transform_raster(self, out_file):
        src_ds = self.in_dataset

        # Define source CRS
        src_crs = osr.SpatialReference()
        src_crs.ImportFromProj4(self.in_file_proj_string)
        src_wkt = src_crs.ExportToWkt()

        # Define target CRS
        dst_crs = osr.SpatialReference()
        dst_crs.ImportFromEPSG(int(self.out_file_crs.split(':')[1]))
        dst_wkt = dst_crs.ExportToWkt()

        error_threshold = 0.125
        resampling = gdal.GRA_NearestNeighbour

        # Call AutoCreateWarpedVRT() to fetch default values for target raster dimensions and geotransform
        tmp_ds = gdal.AutoCreateWarpedVRT(
            src_ds,
            src_wkt,
            dst_wkt,
            resampling,
            error_threshold
        )
        # Create the final warped raster
        try:
            dst_ds = gdal.GetDriverByName('GTiff').CreateCopy(out_file, tmp_ds)
            dst_ds = None
            self.iface.messageBar().pushMessage(
                "Success", "Transformation complete.", level=QgsMessageBar.INFO, duration=3)
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Error", "Transformation failed, please check your configuration. Error was: {}".format(e), level=QgsMessageBar.CRITICAL, duration=3)

    def run(self):
        """Run method that performs all the real work"""

        QObject.connect(self.dlg.in_file_browse, SIGNAL("clicked()"), self.browse_infiles)
        QObject.connect(self.dlg.out_file_browse, SIGNAL("clicked()"), self.browse_outfiles)
        QObject.connect(self.dlg.transformation_picker, SIGNAL("currentIndexChanged(int)"), self.transform_changed)
        if self.dlg.transformation_picker.count() == 0:
            self.dlg.transformation_picker.addItems(self.TRANSFORMATIONS.keys())

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # TODO: Make this work
        help_pressed = False
        if help_pressed:
            help_file = 'Example'
            subprocess.Popen([help_file], shell=True)
            log("Not implemented.")

        # See if OK was pressed
        if result:
            log("Starting transform process...")
            self.in_file = self.dlg.in_file_name.text()
            self.out_file = self.dlg.out_file_name.text()

            if self.in_file_type:
                if not self.out_file:
                    log("No outfile set, writing to default name.")
                    filename, file_extension = os.path.splitext(self.in_file)
                    # Setting up default out file without an extension...
                    out_file = filename + '_transformed'
                    if self.in_file_type == 'VECTOR':
                        out_file += '.shp'
                    else:
                        out_file += '.tiff'
                    self.out_file = out_file
                    self.dlg.out_file_name.setText(self.out_file)

                if self.in_file_type == 'VECTOR':
                    self.transform_vector(self.out_file)
                else:
                    self.transform_raster(self.out_file)
            else:
                self.iface.messageBar().pushMessage(
                    "Error", "Invalid settings...", level=QgsMessageBar.CRITICAL, duration=3)
