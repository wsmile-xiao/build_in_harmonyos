# PROJ

PROJ is a cartographic projections and coordinate transformation library. It
ships the `libproj` C/C++ API and command-line tools such as `proj`, `cs2cs`,
`cct`, `geod`, `gie`, and `projinfo`.

The 9.3.1 OpenHarmony package uses the official OSGeo source archive and builds
the core static library with sqlite3-backed `proj.db` data generation. TIFF,
CURL, and `projsync` are disabled in the first Conan package so MapServer can
consume the core coordinate transformation dependency without pulling the wider
geospatial/network dependency chain.
