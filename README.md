# ICSM NTv2 Transformer QGIS Plugin

A work in progress...


TODO:

Check whether we can handle the GDA2020 CRSs using WKT:

```
PROJCRS["GDA2020 / MGA zone 55",
  BASEGEODCRS["GDA2020",
    DATUM["Geocentric Datum of Australia 2020",
      ELLIPSOID["GRS 1980",6378137,298.257222101,LENGTHUNIT["metre",1.0]]]],
  CONVERSION["Map Grid of Australia zone 55",
    METHOD["Transverse Mercator",ID["EPSG",9807]],
    PARAMETER["Latitude of natural origin",0,ANGLEUNIT["degree",0.01745329252]],
    PARAMETER["Longitude of natural origin",147,ANGLEUNIT["degree",0.01745329252]],
    PARAMETER["Scale factor at natural origin",0.9996,SCALEUNIT["unity",1.0]],
    PARAMETER["False easting",500000,LENGTHUNIT["metre",1.0]],
    PARAMETER["False northing",10000000,LENGTHUNIT["metre",1.0]]],
  CS[cartesian,2],
    AXIS["easting (E)",east,ORDER[1]],
    AXIS["northing (N)",north,ORDER[2]],
    LENGTHUNIT["metre",1.0],
  ID["EPSG",7855]]
  ```