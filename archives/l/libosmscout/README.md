# libosmscout

libosmscout is an OpenStreetMap based offline vector map rendering, routing and
POI search library written in C++17.  It bundles the OSM data importer, the map
style sheet compiler, the routing / POI / basemap databases, a GPX reader and
several drawing backends.

## HarmonyOS PC Adaptation

The HarmonyOS PC recipe builds the dependency-light component set and leaves the
optional backends that cannot be satisfied on this host switched off:

| component | library | notes |
|-----------|---------|-------|
| core | `libosmscout.a` | OSM data model, databases, routing, location search |
| map | `libosmscout_map.a` | painter abstractions, style sheet compiler |
| map-svg | `libosmscout_map_svg.a` | SVG backend (no external dependencies) |
| import | `libosmscout_import.a` | OSM XML reader via libxml2, index generators |
| gpx | `libosmscout_gpx.a` | GPX track reader via libxml2 |
| client | `libosmscout_client.a` | map directory / db abstractions |
| test | `libosmscout_test.a` | upstream test helper library |

`libxml2` is the only external dependency; it enables the OSM XML reader in the
import library and the GPX XML reader.  Qt, libagg, cairo, Pango, GLEW/GLM and
Marisa are not available on the OHOS host, so the corresponding backends, the
demos, the command line tools and the text search index stay disabled - the
upstream build degrades these silently through `find_package(... QUIET)`.

The upstream CTest suite (69 registered tests) is compiled and executed during
`build()`, because a Conan 2 `conan create` never calls the recipe `test()`
method.  The installed test and benchmark executables are pruned from the
package again: unsigned OHOS binaries are unusable for consumers.

## Verification

- Upstream CTest suite: 69/69 passed (`ctest --output-on-failure`, ~32 s)
- Consumer acceptance test (`test_package`): 30 checks covering geometry, GPX
  parsing, OSM XML import, database open, style sheet compilation and SVG
  rendering of the imported data

## Upstream

- Source: https://github.com/Framstag/libosmscout

## Package layout

- `include/osmscout{map,mapsvg,import,gpx,client}/` — public headers
- `lib/libosmscout*.a` — static libraries
- `lib/pkgconfig/*.pc` — upstream pkg-config metadata
- `share/osmscout/stylesheets/` — type configuration (`*.ost`) and style sheets
  (`*.oss`), required at runtime by the map renderer
