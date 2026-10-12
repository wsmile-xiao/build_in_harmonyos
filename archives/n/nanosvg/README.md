# nanosvg

Simple stupid SVG parser and anti-aliased rasterizer (two single-header libraries, Zlib license).

- Upstream: https://github.com/memononen/nanosvg (master branch, Zlib)
- Form factor: two headers — `src/nanosvg.h` (parser, `NANOSVG_IMPLEMENTATION` activates) + `src/nanosvgrast.h` (rasterizer, `NANOSVGRAST_IMPLEMENTATION` activates)
- Zero third-party dependencies (libc/libm only); upstream ships its own CMakeLists.txt (used as-is, zero patches)
- Conan package ships two thin static libraries `libnanosvg.a` + `libnanosvgrast.a` plus the two public headers under `include/nanosvg/`

## Consuming

```c
#include <nanosvg.h>        /* parser */
#include <nanosvgrast.h>    /* rasterizer */

NSVGimage* img = nsvgParse(svgString, "px", 96.0f);
NSVGrasterizer* rast = nsvgCreateRasterizer();
nsvgRasterize(rast, img, 0, 0, 1.0f, rgbaBuffer, w, h, w * 4);
```

With the Conan package, link `NanoSVG::nanosvg` / `NanoSVG::nanosvgrast` (implementation already compiled into the static libraries — do NOT define `NANOSVG_IMPLEMENTATION` / `NANOSVGRAST_IMPLEMENTATION` in consumer code).

## Versions

| Version | Upstream snapshot | Status |
|---------|-------------------|--------|
| 0.0-git.239e102 | master @ 239e102ec2c691f2902e20ace2ed36ee4a35cfe6 | built |
