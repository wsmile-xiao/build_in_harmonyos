# libopenraw-pixbuf-loader

`libopenraw-pixbuf-loader` is the **gdk-pixbuf loader module** that ships inside
the libopenraw source tree (`gnome/pixbuf-loader.c`).  It is built as a shared
module (`libopenraw_pixbuf.so`) that exports `fill_info()` / `fill_vtable()` as
`G_MODULE_EXPORT` entry points and is loaded at runtime by gdk-pixbuf's module
loader.  It registers the "Digital camera RAW" format and lets gdk-pixbuf open
camera RAW files (`.dng .cr2 .crw .nef .orf .pef .arw .erf .mrw .raf`) through
the libopenraw decoder.

**Homepage**: https://libopenraw.freedesktop.org/

**Category**: graphics/library

## Version List

- 0.3.7 (2026-09-25) - built, Conan recipe created

## Dependencies

- libopenraw (decoder; `libopenraw/0.1.2` is the published version — see notes)
- gdk-pixbuf >= 2.22 (`gdk-pixbuf/2.44.6`)
- glib >= 2.0 (transitive, via gdk-pixbuf)
- clang (OHOS llvm toolchain)

## Build Notes

Upstream publishes **no standalone tarball** for this loader; the source is the
official libopenraw 0.3.7 release tarball.  The top-level libopenraw
`configure.ac` cannot be used here — it hard-requires cargo/rustc (the `lib/mp4`
Rust workspace) and would rebuild the libopenraw library proper, which is
packaged separately.  Since the loader is a single C file, the recipe
reproduces the upstream `gnome/Makefile.am` rule directly:

```
libopenraw_pixbuf_la_LDFLAGS = -no-undefined -module -avoid-version
libopenraw_pixbuf_la_LIBADD  = ../lib/libopenraw.la $(LIBGLIB_LIBS) $(LIBGDKPIXBUF_LIBS)
libopenraw_pixbuf_la_SOURCES = pixbuf-loader.c
loaderdir = $(GDK_PIXBUF_DIR)
```

### Conan Recipe Notes

- Built with a single `clang -shared -fPIC` compile of `gnome/pixbuf-loader.c`,
  linked against libopenraw + glib + gdk-pixbuf; compiler/include/lib inputs come
  from the Conan toolchain and dependency `cpp_info` (R33 — no bare shell vars).
- The module is installed into `lib/gdk-pixbuf-2.0/loaders/` and signed with
  `binary-sign-tool -selfSign 1` on OHOS (an unsigned ELF cannot be dlopen'ed).
- `libopenraw` → `boost/1.84.0` pins `zlib/1.3.1` while `gdk-pixbuf` → `glib`
  pins `zlib/1.3.1.1`; the recipe unifies them with
  `self.requires("zlib/1.3.1.1", override=True)`.
- `requires` uses `libopenraw/0.1.2` (the published registry version, R36); the
  0.3.7 API surface is compatible and the package can be re-pointed to
  `libopenraw/0.3.7` once it is published (see `0.3.7/notes.md`).
- `test_package/` dlopens the built+packaged module, asserts the format name,
  extensions, mime types and the incremental-load vtable wiring, and includes
  two negative controls.
