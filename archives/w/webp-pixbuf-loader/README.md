# webp-pixbuf-loader

webp-pixbuf-loader is a GDK Pixbuf loader module that adds WebP image format
support to applications using gdk-pixbuf.  It is built as a shared module
(`libpixbufloader-webp.so`) that gdk-pixbuf loads at runtime via its module
loader mechanism.

**Homepage**: https://github.com/aruiz/webp-pixbuf-loader

**Category**: graphics/library

## Version List

- 0.2.7 (2026-06-05) - built, Conan recipe created

## Dependencies

- libwebp >= 1.3.2 (provides libwebp, libwebpdemux, libwebpmux)
- gdk-pixbuf >= 2.22.0
- meson >= 0.54
- ninja

## Build Notes

webp-pixbuf-loader uses the meson build system.  The module exports
`fill_info()` and `fill_vtable()` as `G_MODULE_EXPORT` entry points,
which gdk-pixbuf calls to register the WebP loader.

### Conan Recipe Notes

- The libwebp conan package exposes only `webp` and `sharpyuv` through
  `cpp_info.libs`, but meson looks for `libwebpdemux` and `libwebpmux` as
  separate pkg-config dependencies.  The conanfile.py `generate()` method
  creates the missing `.pc` files pointing to the libwebp package.
- The `gdk_pixbuf_moduledir` meson option is set to install the module
  into `lib/gdk-pixbuf-2.0/loaders/` within the package.
- On HarmonyOS (OHOS), the shared module is signed with `binary-sign-tool`
  after installation.
- R32: `settings.os` checks use `in ("Linux", "OHOS")`.
- R33: No bare shell variables; all compiler/flags come from Conan Toolchain.
