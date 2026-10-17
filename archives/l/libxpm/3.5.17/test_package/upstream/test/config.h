/*
 * Minimal config.h for the vendored upstream libXpm test programs.
 *
 * Mirrors the defines libXpm's own configure would emit for the OHOS aarch64
 * build.  NO_ZPIPE disables the compressed-pixmap (.xpm.gz / .xpm.Z) variants
 * — the upstream harness skips those cleanly via `#ifdef NO_ZPIPE`
 * (compressed pixmaps need a gzip/compress toolchain + build-time generation
 * step that is not part of the packaged library build).  glib >= 2.70 replaced
 * g_pattern_match_string with g_pattern_spec_match_string; TestAllFiles.h
 * maps the old name to the new one when HAVE_G_PATTERN_SPEC_MATCH_STRING.
 */
#define PACKAGE_BUGREPORT "https://gitlab.freedesktop.org/xorg/lib/libxpm/-/issues"
#define HAVE_G_PATTERN_SPEC_MATCH_STRING 1
#define NO_ZPIPE 1
#define _GNU_SOURCE 1
