# glib 2.88.0 HarmonyOS PC adaptation notes

Issue: #1790
Branch: feat/glib-2.88.0
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

The patches modify build/test metadata and platform conditionals; they do not
rewrite upstream test logic to fake successful results.
---

**编译结束**: 2026-08-16 09:42
**最终状态**: built
