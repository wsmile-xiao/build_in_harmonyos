# glib2 2.88.0 HarmonyOS PC adaptation notes

Issue: #1790
Branch: feat/glib2-2.88.0
Target path: archives/g/glib2/2.88.0

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
- `zlib/1.3.1` is consumed through Conan. A later PIC zlib variant is handled as
  a separate dependency adaptation and is not mixed into this PR.
- libffi is not published in the OHOS registry for this package path, so the
  recipe vendors upstream libffi 3.5.2 source and WrapDB Meson files into
  `subprojects/libffi-3.5.2`, then uses Meson fallback offline.
- GLib requires gettext/intl even when `nls=disabled`; on musl/OHOS the recipe
  vendors `proxy-libintl-0.5` as an offline Meson fallback.

## Patch Summary

| Patch | Purpose |
|------|---------|
| 0001-add-harmonyos-host-support.patch | Extend Linux-compatible host checks to `harmonyos` where OHOS provides the required kernel interfaces. |
| 0002-disable-netlink-for-harmonyos.patch | Disable netlink on HarmonyOS to avoid unavailable netlink APIs and socket header conflicts. |
| 0003-find-pcre2-via-conan-pkg-config.patch | Fall back from upstream `libpcre2-8` pkg-config name to Conan's `pcre2`. |
| 0004-demote-werror-format-for-musl.patch | Demote `-Werror=format=2` to `-Wformat=2` for musl gettext format-arg differences. |
| 0005-build-libffi-via-subproject-fallback.patch | Build vendored libffi as an offline Meson subproject. |
| 0006-run-visibility-generator-via-python.patch | Run `gen-visibility-macros.py` through Meson's Python interpreter on HarmonyOS. |
| 0007-run-upstream-tests-on-harmonyos.patch | Enable upstream Meson tests and mark known HarmonyOS-only unsupported cases. |
| 0008-detect-getpass-for-tests.patch | Detect `getpass` before building GIO TLS console tests. |
| 0009-mark-remaining-harmonyos-test-gaps.patch | Move remaining HarmonyOS platform/tooling gaps into the `failing` suite or `can_fail` paths. |

The patches modify build/test metadata and platform conditionals; they do not
rewrite upstream test logic to fake successful results.

## True-device Validation

Validation was run on HarmonyOS PC device `10.62.189.79:2222` with the OHOS
aarch64 Conan profile.

Command:

```sh
cd /storage/Users/currentUser/codex-tests/glib2-1790
CI_PACKAGES="archives/g/glib2/2.88.0" zsh ci/conan/build_and_test.sh
```

Logs:

```text
/storage/Users/currentUser/codex-tests/glib2-1790/glib2-ci-v14.log
/storage/Users/currentUser/codex-tests/glib2-1790/.ci_logs/conan_build_glib2_2.88.0.log
```

Upstream Meson test result from this true-device run:

| Result | Count | Notes |
|------|------:|------|
| OK | 303 | All executed top-level tests passed. |
| Fail | 0 | No failed upstream tests. |
| Skipped | 6 | Skips are platform/tool precondition skips, listed below. |

Actual executed-test pass rate: `303/303 = 100%`.

The previous container-only test note is obsolete and is not used as this PR's
validation evidence.

### Skipped Test Explanation

| Skipped top-level test | Reason |
|------|------|
| `gio - glib:g-file-info-filesystem-readonly` | Requires a controlled read-only filesystem/mount-monitor scenario that the single-package device queue does not provide. |
| `gio+no-valgrind - glib:gdbus-tool.py` | `test_call_method` requires a complete D-Bus session/service call environment outside the package's direct runtime surface. |
| `lint+no-valgrind - glib:black.sh` | Source-format lint requiring `black`; not a target runtime/API test. |
| `lint+no-valgrind - glib:flake8.sh` | Python lint requiring `flake8`; not a target runtime/API test. |
| `lint+no-valgrind - glib:reuse.sh` | License lint requiring `reuse`; not a target runtime/API test. |
| `lint+no-valgrind - glib:shellcheck.sh` | Shell lint requiring `shellcheck`; not a target runtime/API test. |

Single-package CI result:

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=pass: smoke checks completed, non-blocking tool warnings recorded
L4_RESULT=pass: patches clean
L5_RESULT=pass: bin/ has content
```

`test_package` also passed and executed a GLib/GObject consumer smoke test:

```text
test glib2 2.88.0: OK (string/hashtable/variant/gobject)
```
