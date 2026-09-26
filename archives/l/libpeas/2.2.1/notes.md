# libpeas 2.2.1 for HarmonyOS

## Upstream and build

- Upstream: https://gitlab.gnome.org/GNOME/libpeas, release 2.2.1
- Source archive: https://download.gnome.org/sources/libpeas/2.2/libpeas-2.2.1.tar.xz
- Build system: Meson; Conan 2 recipe name: `libpeas`
- Runtime requirements: `glib/2.88.3` and `proxy-libintl/0.5`
- Build tools: `meson/1.11.0` and `pkgconf/3.0.5` Conan tool requirements; HarmonyOS workers do not provide these commands globally.
- Build shared because the C loader uses `dlopen()` for plugin modules; optional Python, GJS, Lua, Vala, GTK documentation and introspection features are disabled.

## HarmonyOS adaptations

1. `patches/0001-libpeas-peas-i18n.c.patch` calls the exported `libintl_*` symbols directly rather than relying on the `g_libintl_*` aliases from the generated header.
2. `patches/0002-meson.build.patch` removes the unavailable `gi-docgen` subproject fallback.
3. `patches/0003-enable-tests-without-introspection.patch` keeps the upstream C test suites enabled when GIR generation is disabled and guards only the private typelib lookups that require `g-ir-scanner`.
4. The recipe supplies GLib's `glib-genmarshal` and `glib-compile-resources` pkg-config variables through wrappers that set GLib's runtime library path; it also adds `proxy-libintl` to the generated GLib pkg-config link flags.
5. GLib helper wrappers include `glib-compile-schemas` as well as the Meson generators; the schema compiler wrapper sets the packaged GLib runtime path so the C plugin fixture can exercise its GSettings API test.

## Upstream tests

The recipe runs the upstream Meson suite during native HarmonyOS builds using `meson test -v -C <build> --timeout-multiplier=16`. `test_package/MANIFEST.yml` inventories the four test executables and their 54 TAP assertions. Cross builds report that target tests cannot run.

For the local device run, `user.libpeas:source_archive` accepts a pre-staged copy of the release tarball and verifies it against the same pinned SHA-256 before unpacking. The default recipe path still fetches the official GNOME URL.

## Consumer test

`test_package/test_libpeas.c` compiles and executes two GLib test cases against the packaged `libpeas-2` API: engine creation and search-path registration.

## HarmonyOS verification (2026-09-25)

- `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-libpeas conan create archives/l/libpeas/2.2.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing -c user.libpeas:source_archive=/storage/Users/currentUser/work/psj/libpeas6691/source/libpeas-2.2.1.tar.xz`
- Create exit status: 0.
- Upstream Meson suite: `Ok: 4`, `Fail: 0`; TAP plans 18 + 21 + 9 + 6 = 54 assertions, all passed.
- Consumer test: 2/2 (`/libpeas/engine-new`, `/libpeas/engine-add-search-path`).
- Source override archive SHA-256: `589eca89b437006edf3755478df037c740a2a84cfa5d202dbad6095e828e2488`, equal to the pinned official release archive hash. The override is only used for this local device run; normal builds download from `download.gnome.org`.
