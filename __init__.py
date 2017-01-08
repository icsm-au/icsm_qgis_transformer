# -*- coding: utf-8 -*-
"""
/***************************************************************************
 icsm_ntv2_transformer
                                 A QGIS plugin
 This plugin uses official ICSM grids to transform between Australian coordinate systems.
                             -------------------
        begin                : 2017-01-08
        copyright            : (C) 2017 by Alex Leith
        email                : alex@auspatious.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load icsm_ntv2_transformer class from file icsm_ntv2_transformer.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .icsm_qgis_transformer import icsm_ntv2_transformer
    return icsm_ntv2_transformer(iface)
