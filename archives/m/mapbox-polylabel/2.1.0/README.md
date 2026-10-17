# mapbox-polylabel 2.1.0

A fast algorithm for finding the pole of inaccessibility of a polygon.

Upstream v2.1.0 is JavaScript-only: the Conan package installs the versioned
`polylabel.js` ES module under `share/mapbox-polylabel/` with its `LICENSE`.
The upstream gate is the node:test suite (`node --test test/test.js`, 4 tests);
the consumer test imports the packaged file and checks degenerate and square
polygons (4 assertions).

Upstream source: https://github.com/mapbox/polylabel/tree/v2.1.0
