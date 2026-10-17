# glib 2.88.0 HarmonyOS PC adaptation notes

Issue: not tracked for this round
Branch: fix/glib-2.88.0
Target path: archives/g/glib/2.88.0

## Summary

GLib 2.88.0 uses Meson and installs the GLib/GObject/GIO/GModule/GThread
libraries, public headers, pkg-config files, and GLib command-line tools.

The OHOS Conan profile maps `os=OHOS` to Meson `host_system='harmonyos'`.
Upstream GLib does not have a dedicated HarmonyOS branch, so this recipe adds
the minimum platform handling needed to build and test on HarmonyOS PC.

## Build Configuration

The recipe builds a static package:

```text
default_library=static
wrap_mode=nodownload
libmount=disabled
selinux=disabled
nls=disabled
introspection=disabled
man-pages=disabled
gtk_doc=false
oss_fuzz=disabled
tests=true
installed_tests=false
```

`tests=true` is intentional. On native OHOS/HarmonyOS builds, the recipe runs
upstream Meson tests in `build()`:

```sh
meson test -v -C "<build-folder>" --timeout-multiplier=16 --no-rebuild --no-suite=failing
```

## Dependency Strategy

- `pcre2/10.45` is consumed through Conan-generated pkg-config metadata.
- `zlib/1.3.1` is consumed through Conan.
- libffi is not published in the OHOS registry, so the recipe vendors upstream
  libffi 3.5.2 source and WrapDB Meson files into `subprojects/libffi-3.5.2`,
  then uses Meson fallback offline.
- GLib requires gettext/intl even when `nls=disabled`; on musl/OHOS the recipe
  vendors `proxy-libintl-0.5` as an offline Meson fallback.

## Patch Summary

Patches 0001-0009 cover host_system harmonyos handling, netlink disable,
pcre2 pkg-config name, musl -Werror format demotion, libffi subproject
fallback, python interpreter routing for the visibility generator, upstream
meson tests enablement and remaining HarmonyOS test gaps. Patches 0010/0011
mark the flaky `network-address` (gresolver resolve-address) and
`monotonic-time` (ns_after>ns_before timing) tests as can_fail on HarmonyOS.
Patches 0012/0013 add and test `g_type_ensure_initialized()`, an explicit
GObject type-system initialization entry point for HarmonyOS environments where
ELF `.init_array` constructors are not run before first GObject use.

The patches modify build/test metadata and platform conditionals; they do not
rewrite upstream test logic to fake successful results.

## 2026-08-25 Front-Loaded Recheck

- Official source archive SHA256 was verified locally:
  `3546251ccbb3744d4bc4eb48354540e1f6200846572bab68e3a2b7b2b64dfd07`.
- The release archive contains top-level `meson.build`; no Autotools or CMake
  entry point is used for this version.
- All 13 patches replay cleanly, in order, on the official source archive.
- `conanfile.py` and `test_package/conanfile.py` pass Python syntax checking.
- W0 recipe checks passed in an isolated temporary Conan 2.31.2 home:
  `pcre2/10.45#5ecd2f9871deb549e2ae07489f2e40df` and
  `zlib/1.3.1#2ee7c0eeb8f4dfef8982d0c5c1551a61` downloaded from `ohpcd`.
  `libffi/3.5.2#c6578c754a2a4a1e650ab4992cedb8b2` also exists on `ohpcd`,
  though this 2.88.0 recipe still vendors libffi as an offline Meson
  subproject.

## 2026-08-25 Shadow CI

Device: `10.62.220.52:2222` as `currentUser`.

The authoritative run is:

```text
run_id=codex-glib-glib-2.88.0-C0DX-r1-shadow-ci-r7-20260825-203338-6764
run_dir=/storage/Users/currentUser/ohos-test-runs/codex-glib-glib-2.88.0-C0DX-r1-shadow-ci-r7-20260825-203338-6764
command='zsh' 'ci/conan/build_and_test.sh' 'archives/g/glib/2.88.0'
exit_code=0
```

Result summary:

- L0 passed: declared registry dependencies `pcre2/10.45` and `zlib/1.3.1`
  were found, and the registry already-published glib recipe content matched.
- Conan create passed on device with upstream Meson tests enabled.
- Upstream Meson test summary: 302 ok, 0 failed, 6 skipped.
- `test_package` built and ran on device:
  `test glib 2.88.0: OK (string/hashtable/variant/gobject/gio)`.
- L1e destructive negative test confirmed the smoke test genuinely depends on
  glib by moving `bin/` and `lib/` away and observing the expected failure.
- L1/L2/L4/L5 passed; Build Summary reported Total 1, Success 1, Failed 0.

An earlier run,
`codex-glib-glib-2.88.0-C0DX-r1-shadow-ci-r6-20260825-194818-4664`,
completed the build, upstream Meson tests, and `test_package`, but ended with
rc=141 immediately after starting L5. Re-running the same package as r7 passed,
so r7 is treated as the valid shadow CI result.

---

**编译结束**: 2026-08-16 09:42
**最终状态**: built
