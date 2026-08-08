# Source analysis: vips 8.18.4

Upstream source uses Meson. The top-level meson.build requires:

- dependency('glib-2.0', version: '>=2.52')
- dependency('gio-2.0')
- dependency('gobject-2.0')
- dependency('gmodule-no-export-2.0', required: get_option('modules'))
- dependency('expat')
- dependency('threads')
- cc.find_library('m', required: false)

Feature options in meson_options.txt cover codec and integration backends such
as archive, cfitsio, cgif, exif, fftw, fontconfig, heif, highway, imagequant,
jpeg, jpeg-xl, lcms, magick, matio, nifti, openexr, openjpeg, openslide, orc,
pangocairo, pdfium, png, poppler, quantizr, raw, rsvg, spng, tiff, uhdr, webp,
and zlib.

Prior repository notes for vips 8.18.2 recorded OHOS issues around libtiff
static transitive dependencies, pkg-config propagation, toybox rm in Ninja
STATIC_LINKER rules, and dynamic library loading. This W0 recipe avoids those
optional backends for the first package closure and keeps the test_package on
core C API behavior.
