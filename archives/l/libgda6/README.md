# libgda6

GNU Data Access (libgda) 6.0.0 — a unified data-access layer for
SQL/databases, adapted for OpenHarmony PC (aarch64).

- Upstream: https://gitlab.gnome.org/GNOME/libgda
- Version: 6.0.0
- Current package: `archives/l/libgda6/6.0.0`
- Supported OpenHarmony architecture: aarch64
- Requires: glib/2.88.x, libxml2/2.15.x, sqlite3/3.53.x, iso-codes/4.20.x
  (conan deps); tool_requires: vala/0.56.x, intltool/0.51.x

Notes for the OHOS port:

- The SQLite provider is linked statically into `libgda-6.0.so` (the
  conan sqlite3 package ships a static library only, so the upstream
  dlopen path cannot work).
- HMDFS denies `os.symlink` to the conan process tree; the recipe
  materializes the meson soversion/dev links as copies in the build dir
  and in the installed package (`_materialize_soname_files()`).
- Shebang-based glib codegen tools are wrapped in tiny ELF exec shims
  because HMDFS intermittently denies exec to interpreter scripts.
