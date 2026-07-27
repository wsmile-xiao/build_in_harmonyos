# Cattle 1.4.0 OHOS notes

- Upstream uses Autotools and requires GLib, GObject, and GIO 2.38 or newer.
- `glib/2.84.0` is the merged OHOS Conan prerequisite.
- Introspection and GTK-Doc are disabled because they are optional development
  outputs and are not needed by the library or its upstream tests.
- The upstream `check-local` target conditionally uses `gtester`. The recipe
  also directly runs its five upstream test binaries to guarantee nonzero test
  coverage when `gtester` is unavailable.
