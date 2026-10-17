# gupnp-av 0.14.5 HarmonyOS PC adaptation notes

Issue: 无独立 Issue（HarmonyOS PC 三方库适配，积分赛提交）
Branch: feat/gupnp-av-0.14.5
Target path: archives/g/gupnp-av/0.14.5

## Summary

GUPnP A/V is a small utility library for dealing with UPnP A/V profiles:
DIDL-Lite parsing/writing, MediaServer search criteria parsing, protocol
info handling and CDS LastChange parsing. Pure C, LGPL-2.1-or-later, built
with Meson.

⭐ Key fact verified against upstream meson.build: gupnp-av 0.14.5 depends
ONLY on glib-2.0/gobject-2.0 (>= 2.58) + libxml-2.0. It does NOT depend on
gupnp/gssdp — the "gupnp" in the name is ecosystem branding only; the
library itself is a DIDL-Lite XML parsing/writing library. Downstream
`gupnp` consumers link it, but building gupnp-av itself needs neither.

## Build Configuration

The recipe builds a static package:

```text
default_library=static
wrap_mode=nodownload
introspection=false
vapi=false
gtk_doc=false
tests=true
```

- `introspection=false` is required: the default `true` pulls
  `g-ir-scanner`/gir generation which is unavailable on the build host.
- `vapi=false`: the `vala/` subdir is only entered when
  `introspection and vapi`, so this is skipped automatically.
- `gtk_doc=false`: skips gi-docgen.
- `tests=true`: tests/ and tests/gtest/ test targets are always built by
  meson (`subdir('tests')` is unconditional in meson.build), kept enabled
  so the recipe can run the upstream test suite on-device.

## Dependency Strategy

- `glib2/2.88.0` (registry, verified via `conan download --only-recipe`):
  its PkgConfigDeps output already provides `glib-2.0.pc`,
  `gobject-2.0.pc` and `gio-2.0.pc` with Version 2.88.0 — no forwarding
  hack needed (unlike the glib2 recipes of the graphene 1.10.8 era).
- `libxml2/2.15.3.1` (registry, verified via `conan download --only-recipe`).
- `gnome.genmarshal` needs the `glib-genmarshal` tool. The glib2 package
  ships `bin/glib-genmarshal` as a python3 script, runnable on the build
  host. The recipe rewrites the `glib_genmarshal=${bindir}/glib-genmarshal`
  variable inside the generated `glib-2.0.pc` to the absolute in-package
  path (same approach as archives/a/atk/2.38.0.1.1).
- OHOS static links need `libintl.a` from the glib2 package passed
  explicitly via `c_link_args` (glib2 .pc files carry `-lintl`).

## Patch Summary

| Patch | Purpose |
|------|---------|
| (none) | Round 1 static build, no patches required. |

## True-device Validation

Upstream meson test result (run on the HarmonyOS PC device, OHOS aarch64
Conan profile, `meson test -v --timeout-multiplier=16 --no-rebuild` in the
conan build folder):

| Result | Count | Notes |
|------|------:|------|
| Ok | 8 | 3 top-level + 5 gtest suites |
| Fail | 0 | No failed upstream tests. |
| Skipped | 0 | No platform/tooling skips. |

Test detail (8 targets, all passed, 19 gtest subtests + top-level checks):

- `gupnp-av:check-search` OK — 4 assertions (TAP dots)
- `gupnp-av:check-feature-list-parser` OK
- `gupnp-av:fragments` OK
- `gupnp-av:test-regression` OK — 5 subtests (bugs/gnome/674319,
  687462, 705564, 770174, 11)
- `gupnp-av:test-didl-lite-object` OK — 1 subtest (namespace-getters)
- `gupnp-av:test-media-collection` OK — 7 subtests (collection
  construction/parse/create/reparent)
- `gupnp-av:test-last-change-parser` OK — 5 subtests
- `gupnp-av:test-cds-last-change-parser` OK — 1 subtest

Actual executed-test pass rate: `8/8 = 100%` (0 failed, 0 skipped).

`test_package` smoke test calls real APIs and passed:

```text
gupnp-av/0.14.5 (test package): RUN: /data/service/hnp/bin/bash -c './test_gupnp_av'
gupnp-av didl-lite/protocol-info/search-criteria OK
```

## Skipped Test Explanation

No upstream tests skipped. `introspection=false` only disables gir/vapi
artifact generation (build-time API bindings codegen), which is not part
of the upstream meson test suite.

## 编译结束

W3 conan create 通过（package_id=43369ca09edbcb99feb39f897ef2373d062d65e9），
上游 meson test 8/8 通过，test_package 通过。归档打包完成。
---

**编译结束**: 2026-09-03 22:23
**最终状态**: published
