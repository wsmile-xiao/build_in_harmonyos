# gtkdatabox 1.0.0 OpenHarmony PC notes

## Scope

This package adapts the official gtkdatabox 1.0.0 Autotools project for OpenHarmony PC. gtkdatabox installs the `libgtkdatabox` library, public headers, and the `gtkdatabox.pc` pkg-config metadata used by GTK+ 3 consumers.

## Dependency boundary

gtkdatabox depends on the GTK+ 3 stack:

- `gtk+-3.0`
- `gdk-3.0`
- `pango`
- `cairo`

The current OHPCD Conan remote does not provide a complete GTK+ 3 Conan dependency chain. This recipe therefore uses the already installed OpenHarmony system prefix. The default prefix is:

```bash
/storage/Users/currentUser/usr/local
```

The prefix can be overridden with `GTK_PREFIX` or `DEFAULT_PREFIX`. On environments where GTK+ is deployed under `/data/service/hnp`, the recipe also searches HNP package roots for `gtk+-3.0.pc` and uses that prefix automatically.

## Build

The package uses upstream Autotools without source patches. Optional integrations that are not required by the library are disabled:

```text
--disable-glade
--disable-gtk-doc
--disable-gtk-doc-html
--disable-gtk-doc-pdf
```

On OHOS, `config.status` creates its temporary awk files with `mktemp -d ./confXXXXXX`, which HMDFS cannot execute. The recipe patches `configure` to use `$HOME/.gtkdatabox-config-tmp` instead (same E114 workaround used by BIRD).

The recipe exports `PKG_CONFIG_PATH`, `CPPFLAGS`, `LDFLAGS`, `PATH`, and `LD_LIBRARY_PATH` for the GTK+ system prefix before configure/build/install. On OHOS it also prepends all HNP-installed pkg-config directories (`/data/service/hnp/*/*/lib/pkgconfig`) because the deployed `glib-2.0.pc`/`gobject-2.0.pc` declare private requirements such as `libpcre2-8` and `libffi` that are installed by HNP rather than under the GTK prefix. The deployed prefix stores runtime GTK dependency shared objects under `lib/external` but omits `cairo-gobject.pc`/`epoxy.pc` and the unversioned linker symlinks (`libcairo-gobject.so`, `libepoxy.so`); the recipe generates the missing pkg-config files, creates the linker symlinks, adds `lib/external` to `LDFLAGS`/`LD_LIBRARY_PATH`, and appends only the HNP runtime fallback dirs that provide `pcre2`/`ffi`/`expat`/`intl` so an older HNP GLib is never loaded.

## Tests

The upstream 1.0.0 archive includes examples and generated marshaller checks. The recipe now runs the upstream Autotools `make check` target, builds all 14 upstream `examples/` programs, and launches every example with timeout when target execution is available. A timeout after successful startup is accepted because the upstream examples are interactive GTK programs and do not exit by themselves. On the headless OpenDesk device, each example loads all dependencies and reaches GTK initialization, and exits with the expected `cannot open display` error, which the recipe accepts (exit 1) as a startup/linkage probe.

The `test_package` verifies package consumption by:

1. Resolving `gtkdatabox` through the installed pkg-config file.
2. Compiling and linking a small GTK+ consumer against `libgtkdatabox`.
3. Running a widget smoke check when the target binary can execute: it verifies type registration, creates a `GtkDataboxPoints` graph from sample data, verifies graph type registration, and exercises graph hide and size accessors; it instantiates a GtkDatabox widget when `gtk_init_check()` finds a display backend.

On the headless CI worker the runtime smoke step is skipped because that worker's deployed GTK stack omits `libfribidi.so.0`, `libcairo-gobject.so.2`, and `libepoxy.so.0` from the loader search path; the OpenDesk device run already covers the runtime smoke checks.

The current package scope verifies build, linkage, type registration, data graph creation, graph hide and size accessors, and display-backed widget construction. Full interactive rendering and pointer input behavior on OpenHarmony PC still require manual validation before claiming complete UI adaptation.

Declared package test pass rate (OpenDesk `20260814-030728-8a33ba-3056-expanded-tests2`): `conan create` passed. Upstream `make check` reports 0/0; all 14 upstream examples build and each startup probe reaches GTK init on the headless device (display-open failure accepted); the `test_package` consumer smoke test passed 76/76 executed assertions on the headless OpenDesk device; the full 93 assertions run when a GTK display is available.

## Verification command

```bash
CI_PACKAGES="archives/g/gtkdatabox/1.0.0" zsh ci/conan/build_and_test.sh
```

## Manual validation note

R40 manual validation marker: Headless CI covers build, linkage, graph object creation, graph hide and size accessors, and non-rendering smoke checks. GtkDatabox interactive plotting, pointer input, and GTK backend rendering require an OpenHarmony PC display session. This PR must remain at `partial` status until that manual validation is complete; it must not be promoted to `published` based only on CI smoke tests.
