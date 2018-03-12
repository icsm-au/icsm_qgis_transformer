# -*- coding: utf-8 -*-
"""
/***************************************************************************
 icsm_ntv2_transformerDialog
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

import os

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'icsm_qgis_transformer_dialog_base.ui'))


class icsm_ntv2_transformerDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(icsm_ntv2_transformerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
