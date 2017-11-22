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

import os
import os.path
import tempfile
import webbrowser
from collections import namedtuple

from gdalconst import GA_ReadOnly
from osgeo import gdal, osr

from icsm_qgis_transformer_dialog import icsm_ntv2_transformerDialog
from PyQt4.QtCore import (SIGNAL, QCoreApplication, QFileInfo, QObject,
                          QSettings)
from PyQt4.QtGui import QAction, QFileDialog, QIcon
from qgis.core import (QgsCoordinateReferenceSystem, QgsMapLayerRegistry,
                       QgsMessageLog, QgsRasterLayer, QgsVectorFileWriter,
                       QgsVectorLayer)
from qgis.gui import QgsMessageBar

Transform = namedtuple(
    'Transform',
    ['name', 'source_name', 'target_name', 'source_proj', 'target_proj', 'source_code', 'target_code', 'grid', 'grid_text'],
)

# Get urlretrieve from the right spot. Can be simplified to the second method when we're only Python3.
try:
    from urllib import urlretrieve
except ImportError:
    from urllib.request import urlretrieve

# This is the GitHub source
GRID_FILE_SOURCE = "https://github.com/icsm-au/transformation_grids/raw/master/"
# This is the AWS S3 source
GRID_FILE_SOURCE = "https://s3-ap-southeast-2.amazonaws.com/transformation-grids/"


def update_local_file(remote_url, local_file):
    try:
        out_file, result = urlretrieve(remote_url, local_file)
    except IOError:
        log("Failed to download .GSB file.", True)
        return False

    try:
        content_length = result['Content-Length']
        if content_length < 1000:
            os.remove(local_file)
            log("Failed to download file. Please contact support.")
        else:
            log("Successfully download file of size {} to {}".format(content_length, local_file))
    except KeyError:
        os.remove(local_file)
        if result.get('Status'):
            log("Failed to download file with error: {}".format(result['Status']))
        else:
            log("Failed to download file unexpected error: {}".format(result))
        return False
    return True


def log(message, error=False):
    log_level = QgsMessageLog.INFO
    if error:
        log_level = QgsMessageLog.CRITICAL
    QgsMessageLog.logMessage(message, 'ICSM NTv2 Transformer', level=log_level)


class icsm_ntv2_transformer:
    """QGIS Plugin Implementation."""
    AGD66GRID = os.path.dirname(__file__) + '/grids/A66_National_13_09_01.gsb'
    AGD84GRID = os.path.dirname(__file__) + '/grids/National_84_02_07_01.gsb'
    GDA2020CONF = os.path.dirname(__file__) + '/grids/GDA94_GDA2020_conformal.gsb'
    GDA2020CONF_DIST = os.path.dirname(__file__) + '/grids/GDA94_GDA2020_conformal_and_distortion.gsb'

    # These comments are printed in the dialog that describes the transform to be carried out.
    GRID_COMMENTS = {
        'A66_National_13_09_01.gsb': (
            "NTv2 transformation grid A66_national_13_09_01.gsb [EPSG:1803] <b>provides complete national coverage.</b><br>"
            "See Appendix A of Geocentric Datum of Australia 2020 Technical Manual for grid coverage and description."
        ),
        'National_84_02_07_01.gsb': (
            "NTv2 transformation grid National_84_02_07_01.gsb [EPSG:1804] <b>only has coverage for jurisdictions that adopted AGD84 - QLD, SA and WA.</b><br>"
            "See Appendix A of Geocentric Datum of Australia 2020 Technical Manual for grid coverage and description."
        ),
        'GDA94_GDA2020_conformal.gsb': (
            "<b>WARNING! Currently only covers Tasmania.</b><br>"
            "NTv2 transformation grid GDA94_GDA2020_conformal.gsb [EPSG:????] <b>only applies a conformal transformation between the datums.</b><br>"
            "See Section 3.6.1 of Geocentric Datum of Australia 2020 Technical Manual for a description of the grid and when it is appropriate to apply."
        ),
        'GDA94_GDA2020_conformal_and_distortion.gsb': (
            "<b>WARNING! Currently only covers Tasmania.</b><br>"
            "NTv2 transformation grid GDA94_GDA2020_conformal_and_distortion.gsb [EPSG:????] <b>applies a conformal plus distortion transformation between the datums.</b><br>"
            "See Section 3.6.1 of Geocentric Datum of Australia 2020 Technical Manual for a description of the grid and when it is appropriate to apply."
        )
    }

    # EPSGs, in code: name, utm, proj, grid
    available_epsgs = {
        '202': {
            "name": "AGD66 / AMG",
            "utm": True,
            "proj": '+proj=utm +zone={zone} +south +ellps=aust_SA +towgs84=-117.808,-51.536,137.784,0.303,0.446,0.234,-0.29 +units=m +no_defs +nadgrids=' + AGD66GRID + ' +wktext',
            "grid": AGD66GRID
        },
        '203': {
            "name": "AGD84 / AMG",
            "utm": True,
            "proj": '+proj=utm +zone={zone} +south +ellps=aust_SA +towgs84=-134,-48,149,0,0,0,0 +units=m +no_defs +nadgrids=' + AGD84GRID + ' +wktext',
            "grid": AGD84GRID
        },
        '283': {
            "name": "GDA94 / MGA",
            'utm': True,
            "proj": '+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +wktext',
            "grid": None
        },
        '283c': {
            "name": "GDA94 / MGA (Conformal only)",
            'utm': True,
            "proj": '+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +nadgrids=' + GDA2020CONF + ' +wktext',
            "grid": GDA2020CONF
        },
        '283d': {
            "name": "GDA94 / MGA (Conformal and distortion",
            'utm': True,
            "proj": '+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +nadgrids=' + GDA2020CONF_DIST + ' +wktext',
            "grid": GDA2020CONF_DIST
        },
        '78c': {
            "name": "GDA2020 / MGA (Conformal only)",
            'utm': True,
            "proj": '+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +wktext',
            "grid": None
        },
        '78d': {
            "name": "GDA2020 / MGA (Conformal & Distortion)",
            'utm': True,
            "proj": '+proj=utm +zone={zone} +south +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs +wktext',
            "grid": None
        },
        '4202': {
            "name": "AGD66 Latitude and Longitude",
            "utm": False,
            "proj": '+proj=longlat +ellps=aust_SA +towgs84=-117.808,-51.536,137.784,0.303,0.446,0.234,-0.29 +no_defs +nadgrids=' + AGD66GRID + ' +wktext',
            "grid": AGD66GRID
        },
        '4203': {
            "name": "AGD84 Latitude and Longitude",
            "utm": False,
            "proj": '+proj=longlat +ellps=aust_SA +no_defs +towgs84=-134,-48,149,0,0,0,0 +nadgrids=' + AGD84GRID + ' +wktext',
            "grid": AGD84GRID
        },
        '4283': {
            "name": "GDA94 Latitude and Longitude",
            "utm": False,
            "proj": None,
            "grid": None
        },
        '4283c': {
            "name": "GDA94 Latitude and Longitude (Conformal only)",
            "utm": False,
            "proj": '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +nadgrids=' + GDA2020CONF + ' +wktext',
            "grid": GDA2020CONF
        },
        '4283d': {
            "name": "GDA94 Latitude and Longitude (Conformal & Distortion)",
            "utm": False,
            "proj": '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +nadgrids=' + GDA2020CONF_DIST + ' +wktext',
            "grid": GDA2020CONF_DIST
        },
        '7844c': {
            "name": "GDA2020 Latitude and Longitude (Conformal only)",
            "utm": False,
            "proj": '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +wktext',
            "grid": None
        },
        '7844d': {
            "name": "GDA2020 Latitude and Longitude (Conformal & Distortion)",
            "utm": False,
            "proj": '+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs +wktext',
            "grid": None
        }
    }

    # Supported Transforms. This is loaded dynamically because it's big.
    SUPPORTED_TRANSFORMS = {
        # Transform('name', 'source_name', 'target_name', 'source_proj', 'target_proj', 'grid')
    }
    TRANSFORMS = []

    # This gets populated with a transform when a valid dataset is loaded.
    SELECTED_TRANSFORM = None

    # Range makes a list from 49 to 56
    available_zones = range(49, 57)

    # transformations - a list of FROM and all available TOs
    transformations = [
        # UTM
        ['202', ['283']],
        ['203', ['283']],
        ['283', ['202', '203']],
        ['283c', ['78c']],
        ['283d', ['78d']],
        ['78c', ['283c']],
        ['78d', ['283d']],
        # LonLat
        ['4202', ['4283']],
        ['4203', ['4283']],
        ['4283', ['4202', '4203']],
        ['4283c', ['7844c']],
        ['4283d', ['7844d']],
        ['7844c', ['4283c']],
        ['7844d', ['4283d']],
    ]

    def build_transform(self, in_info, in_crs, zone=False):
        source_name = in_info['name']
        source_proj = in_info['proj']
        source_grid = in_info['grid']
        source_epsg = in_crs[0].replace('c', '').replace('d', '')
        source_target_epsgs = in_crs[1]
        zone_string = ""
        if zone:
            zone_string = str(zone)

        source_code = '{epsg}{zone}'.format(epsg=source_epsg, zone=zone_string)
        epsg_string = 'EPSG:{}'.format(source_code)
        name_string = "{name} [EPSG:{code}]"

        if zone and source_proj:
            source_proj = source_proj.format(zone=zone)

        target_crs = []
        for target_epsg in source_target_epsgs:
            target_name = self.available_epsgs[target_epsg]['name']
            # log("Working on {} with {}".format(source_name, target_name))
            target_grid = self.available_epsgs[target_epsg]['grid']
            target_epsg_clean = target_epsg.replace('c', '').replace('d', '')
            target_code = '{epsg}{zone}'.format(
                epsg=target_epsg_clean,
                zone=zone_string
            )
            name = source_name.split(' ')[0] + ' to ' + target_name.split(' ')[0]
            source = name_string.format(name=source_name, code=source_code)
            target = name_string.format(name=target_name, code=target_code)
            target_proj = self.available_epsgs[target_epsg]['proj']

            if zone and target_proj:
                target_proj = target_proj.format(zone=zone)

            grid = None
            if source_grid:
                grid = source_grid
            elif target_grid:
                grid = target_grid
            grid_text = ""
            if grid:
                grid_text = "using NTv2 grid: '{}'".format(os.path.basename(grid))
                comments = self.GRID_COMMENTS.get(os.path.basename(grid))
                grid_text += "<br><br>" + comments

            target_crs.append(Transform(name, source, target, source_proj, target_proj, int(source_code), int(target_code), grid, grid_text))

        return epsg_string, target_crs

    def prepare_transforms(self):
        for source_crs in self.transformations:
            epsg_info = self.available_epsgs[source_crs[0]]
            if epsg_info['utm']:
                # This is a UTM crs, so process all the codes
                for zone in self.available_zones:
                    transform_label, transforms = self.build_transform(epsg_info, source_crs, zone=zone)
                    # If there's more than one transform source that is the same, handle it here
                    existing_transforms = self.SUPPORTED_TRANSFORMS.get(transform_label)
                    if existing_transforms:
                        transforms.extend(existing_transforms)

                    self.SUPPORTED_TRANSFORMS[transform_label] = transforms
            else:
                # Just process this one, no zones
                transform_label, transforms = self.build_transform(epsg_info, source_crs)
                # If there's more than one transform source that is the same, handle it here
                existing_transforms = self.SUPPORTED_TRANSFORMS.get(transform_label)
                if existing_transforms:
                    transforms.extend(existing_transforms)
                self.SUPPORTED_TRANSFORMS[transform_label] = transforms

    def update_transform_text(self, text):
        self.dlg.transform_text.setHtml(text)

    def transform_changed(self):
        self.validate_source_transform()

    def get_dest_crs(self, source_crs):
        this_source_crs = self.SUPPORTED_TRANSFORMS[self.in_file_crs]

        dest_crs = self.CRS_STRINGS[this_source_crs[2]][0]
        zone = this_source_crs[3]

        if zone:
            dest_crs = dest_crs.format(zone=zone)

        return dest_crs

    def get_source_proj_string(self, source_crs):
        this_source_crs = self.SUPPORTED_TRANSFORMS[self.in_file_crs]

        proj_string = self.CRS_STRINGS[this_source_crs[1]][1]
        zone = this_source_crs[3]

        if zone:
            proj_string = proj_string.format(zone=zone)

        return proj_string

    def validate_source_transform(self, in_file_crs=None):
        # Check if there's an in_file
        if not self.in_file and not self.in_file_type:
            self.update_transform_text("Select an input file.")
            return

        if in_file_crs:
            # Set up a new CRS transform environment, as the in_file has changed
            if in_file_crs in self.SUPPORTED_TRANSFORMS:
                log("Selected CRS is supported")
                self.TRANSFORMS = self.SUPPORTED_TRANSFORMS[in_file_crs]
                self.SELECTED_TRANSFORM = self.TRANSFORMS[0]

                self.dlg.out_crs_picker.clear()
                for transform in self.TRANSFORMS:
                    self.dlg.out_crs_picker.addItems([transform.target_name])
            else:
                log("Selected CRS is NOT supported.")
                self.in_file_type = None
                self.update_transform_text("The CRS {} for the selected input file is not supported.".format(in_file_crs))
                return
        else:
            if self.dlg.out_crs_picker.currentIndex() != -1:
                # Change the selected transform
                self.SELECTED_TRANSFORM = self.TRANSFORMS[self.dlg.out_crs_picker.currentIndex()]
            else:
                # Something's gone wrong
                self.update_transform_text("Unable to identify the source file's CRS...")
                return

        self.update_transform_text("Source CRS is {}<br>Destination CRS is {}<br><br>Transforming from {} {}".format(
            self.SELECTED_TRANSFORM.source_name,
            self.SELECTED_TRANSFORM.target_name,
            self.SELECTED_TRANSFORM.name,
            self.SELECTED_TRANSFORM.grid_text))

    def update_infile(self):
        newname = self.dlg.in_file_name.text()

        # Clear out dialogs
        self.in_file_type = None
        self.in_file_crs = None
        self.dlg.out_crs_picker.clear()

        if not os.path.isfile(newname):
            log("There's no file at {}. Ignoring.".format(newname))
            return
        else:
            log("Updating in file")

        fail = False
        layer = QgsVectorLayer(newname, 'in layer', 'ogr')
        if layer.isValid():
            # We have a vector!
            log("Recognised vector layer")
            self.in_file_type = 'VECTOR'
            in_file_crs = layer.crs().authid()
            self.validate_source_transform(in_file_crs)
            self.in_dataset = layer
        else:
            dataset = gdal.Open(newname, GA_ReadOnly)
            if dataset is None:
                fail = True
            else:
                # We have a raster!
                log("Recognised raster layer")
                self.in_file_type = 'RASTER'

                layer = QgsRasterLayer(newname, 'in raster')
                in_file_crs = layer.crs().authid()
                layer = None

                self.validate_source_transform(in_file_crs)

                self.in_dataset = dataset
        if fail:
            self.iface.messageBar().pushMessage(
                "Error", "Couldn't read 'in file' {} as vector or raster".format(newname), level=QgsMessageBar.CRITICAL, duration=3)
            self.update_transform_text("Couldn't read 'In file.'")
        else:
            self.dlg.in_file_name.setText(newname)

    def browse_infiles(self):
        log("Browsing in files")
        newname = QFileDialog.getOpenFileName(
            None, "Input File", self.dlg.in_file_name.displayText(), "Any supported filetype (*.*)")
        if newname:
            self.dlg.in_file_name.setText(newname)

    def browse_outfiles(self):
        log("Browsing out files")
        newname = QFileDialog.getSaveFileName(
            None, "Output file", self.dlg.out_file_name.displayText(), "Shapefile or TIFF (*.shp *.tiff *.tif)")

        if newname:
            log("Out file newname {}".format(newname))
            self.dlg.out_file_name.setText(newname)

    def get_epsg(self, layer):
        return layer.crs().authid().split(':')[1]

    def transform_vector(self, out_file):
        log("Transforming file to: {}".format(out_file))
        layer = self.in_dataset

        source_crs = QgsCoordinateReferenceSystem()
        if self.SELECTED_TRANSFORM.source_proj:
            log("Source from proj")
            log(self.SELECTED_TRANSFORM.source_proj)
            source_crs.createFromProj4(self.SELECTED_TRANSFORM.source_proj)
        else:
            log("Source from id")
            source_crs.createFromId(self.SELECTED_TRANSFORM.source_code)

        log("Setting Source CRS")
        layer.setCrs(source_crs)

        if self.SELECTED_TRANSFORM.target_proj:
            log("Setting intermediate CRS from proj")
            log(self.SELECTED_TRANSFORM.target_proj)
            temp_crs = QgsCoordinateReferenceSystem()
            temp_crs.createFromProj4(self.SELECTED_TRANSFORM.target_proj)

            # We do an intermediate transform, so that the target gets a proper SRID
            temp_dir = tempfile.mkdtemp()
            temp_outfilename = os.path.join(temp_dir, 'temp_file.shp')
            log("Tempfile is: {}".format(temp_outfilename))
            # log(temp_outfilename)
            error = QgsVectorFileWriter.writeAsVectorFormat(layer, temp_outfilename, 'utf-8', temp_crs, 'ESRI Shapefile')
            if error == QgsVectorFileWriter.NoError:
                log("Success on intermediate transform")
                # These overwrite the original target layer destination file.
                layer = QgsVectorLayer(temp_outfilename, 'in layer', 'ogr')
                # The next transform is from and to the destination transform, which is needed to define the CRS properly.
                intermediary_crs = QgsCoordinateReferenceSystem()
                intermediary_crs.createFromId(self.SELECTED_TRANSFORM.target_code)
                layer.setCrs(intermediary_crs)
            else:
                log("Error writing vector, code: {}".format(str(error)))
                self.iface.messageBar().pushMessage(
                    "Error", "Transformation failed, please check your configuration.", level=QgsMessageBar.CRITICAL, duration=3)
                return

        log("Setting final target CRS from id")
        dest_crs = QgsCoordinateReferenceSystem()
        dest_crs.createFromId(self.SELECTED_TRANSFORM.target_code)

        error = QgsVectorFileWriter.writeAsVectorFormat(layer, out_file, 'utf-8', dest_crs, 'ESRI Shapefile')
        if error == QgsVectorFileWriter.NoError:
            log("Success")
            self.iface.messageBar().pushMessage(
                "Success", "Transformation complete.", level=QgsMessageBar.INFO, duration=3)
            if self.dlg.TOCcheckBox.isChecked():
                log("Opening file {}".format(out_file))
                basename = QFileInfo(out_file).baseName()
                vlayer = QgsVectorLayer(out_file, str(basename), "ogr")
                if vlayer.isValid():
                    QgsMapLayerRegistry.instance().addMapLayers([vlayer])
                else:
                    log("vlayer invalid")
        else:
            log("Error writing vector, code: {}".format(str(error)))
            self.iface.messageBar().pushMessage(
                "Error", "Transformation failed, please check your configuration.", level=QgsMessageBar.CRITICAL, duration=3)

    def transform_raster(self, out_file):
        log("Transforming raster to: {}".format(out_file))
        src_ds = self.in_dataset

        # Define source CRS
        src_crs = osr.SpatialReference()
        if self.SELECTED_TRANSFORM.source_proj:
            log("Source from proj")
            src_crs.ImportFromProj4(self.SELECTED_TRANSFORM.source_proj)
        else:
            log("Source from code")
            src_crs.ImportFromEPSG(self.SELECTED_TRANSFORM.source_code)
        src_wkt = src_crs.ExportToWkt()

        # Define target CRS
        dst_crs = osr.SpatialReference()
        if self.SELECTED_TRANSFORM.target_proj:
            log("Target from proj")
            dst_crs.ImportFromProj4(self.SELECTED_TRANSFORM.target_proj)
        else:
            log("Target from code")
            dst_crs.ImportFromEPSG(self.SELECTED_TRANSFORM.target_code)
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
            if '.tif' not in out_file:
                out_file += '.tiff'
            dst_ds = gdal.GetDriverByName('GTiff').CreateCopy(out_file, tmp_ds)

            # If we transformed using Proj, set the CRS using the EPSG code
            if self.SELECTED_TRANSFORM.target_proj:
                srs = 'EPSG:{}'.format(self.SELECTED_TRANSFORM.target_code)
                sr = osr.SpatialReference()
                if sr.SetFromUserInput(srs) != 0:
                    log('Failed to process SRS definition: {}'.format(srs))
                    self.iface.messageBar().pushMessage(
                        "Error", "Failed to assign EPSG code, this may mean that you need a newer QGIS install.",
                        level=QgsMessageBar.CRITICAL, duration=3)
                else:
                    wkt = sr.ExportToWkt()
                    dst_ds.SetProjection(wkt)
            dst_ds = None

            self.iface.messageBar().pushMessage(
                "Success", "Transformation complete.", level=QgsMessageBar.INFO, duration=3)
            if self.dlg.TOCcheckBox.isChecked():
                basename = QFileInfo(out_file).baseName()
                rlayer = QgsRasterLayer(out_file, str(basename))
                if rlayer.isValid():
                    QgsMapLayerRegistry.instance().addMapLayers([rlayer])
                else:
                    self.iface.messageBar().pushMessage(
                        "Error", "Couldn't read output raster, process unsuccessful.",
                        level=QgsMessageBar.CRITICAL, duration=3
                    )
                    log("rlayer invalid")
        except Exception as e:
            self.iface.messageBar().pushMessage(
                "Error", "Transformation failed, please check your configuration. Error was: {}".format(e), level=QgsMessageBar.CRITICAL, duration=3)

    def __init__(self, iface):
        self.dialog_initialised = False
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&ICSM NTv2 Transformer')
        self.toolbar = self.iface.addToolBar(u'icsm_ntv2_transformer')
        self.toolbar.setObjectName(u'icsm_ntv2_transformer')

        self.in_file = None
        self.out_file = None

        self.in_dataset = None

        self.in_file_type = None

        # This build the list of available transforms.
        self.prepare_transforms()

        # This changes the settings (a bit rude of us) to prompt for unknown CRSs
        QSettings().setValue("/Projections/defaultBehaviour", "prompt")

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

        self.update_transform_text("Choose an in file to get started.")

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

    def help_pressed(self):
        help_file = 'file:' + os.path.dirname(__file__) + '/help/icsm_ntv2_transformer_docs.pdf'
        log("Help button pressed. Opening {}".format(help_file))
        webbrowser.open_new(help_file)

    def run(self):
        """Run method that performs all the real work"""

        # Set up the signals.
        if not self.dialog_initialised:
            QObject.connect(self.dlg.in_file_browse, SIGNAL("clicked()"), self.browse_infiles)
            QObject.connect(self.dlg.help_button, SIGNAL("clicked()"), self.help_pressed)
            QObject.connect(self.dlg.in_file_name, SIGNAL("textChanged(QString)"), self.update_infile)
            QObject.connect(self.dlg.out_file_browse, SIGNAL("clicked()"), self.browse_outfiles)
            QObject.connect(self.dlg.out_crs_picker, SIGNAL("currentIndexChanged(int)"), self.transform_changed)
            self.dialog_initialised = True

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            if not self.SELECTED_TRANSFORM:
                log("No transform available, closing.")
                self.iface.messageBar().pushMessage(
                    "Error", "No transformation available...", level=QgsMessageBar.CRITICAL, duration=3)
                return
            log("Checking whether we need a file.")
            required_grid = self.SELECTED_TRANSFORM.grid
            log(required_grid)
            success_downloading = True
            if not os.path.isfile(required_grid):
                grid_file = os.path.basename(required_grid)
                remote_file = GRID_FILE_SOURCE + grid_file
                log("Updating local grid file file {} from {}".format(grid_file, remote_file))

                self.update_transform_text("Downloading required grid file, please wait...")

                success_downloading = update_local_file(remote_file, required_grid)

            if not success_downloading:
                self.update_transform_text("Failed to download transformation grid...")
                self.iface.messageBar().pushMessage(
                    "Error", "Failed to download transformation grid. Check your network connection and try again.", level=QgsMessageBar.CRITICAL, duration=5)

            else:
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
                    else:
                        # Validate the out file name and extension
                        log("Validating out file name")
                        extension = os.path.splitext(self.out_file)[1][1:].lower()
                        directory = os.path.dirname(self.out_file)
                        if os.path.isdir(directory):
                            log("File path includes directory")
                        else:
                            log("File path does not include directory")
                            directory = os.path.dirname(self.in_file)
                            self.out_file = os.path.join(directory, self.out_file)

                        if extension not in ['shp', 'tiff', 'tif']:
                            log("Extension was {}, which is invalid. Adding extension".format(extension))
                            self.out_file.replace(extension, '')
                            if self.in_file_type == 'VECTOR':
                                self.out_file = self.out_file + '.shp'
                            else:
                                self.out_file = self.out_file + '.tiff'
                            self.dlg.out_file_name.setText(self.out_file)

                    if self.in_file_type == 'VECTOR':
                        self.transform_vector(self.out_file)
                    else:
                        self.transform_raster(self.out_file)
                else:
                    self.iface.messageBar().pushMessage(
                        "Error", "Invalid settings...", level=QgsMessageBar.CRITICAL, duration=3)
                self.update_transform_text("Finished processing...")
