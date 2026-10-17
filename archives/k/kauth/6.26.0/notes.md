# kauth 6.26.0 notes

## Scope

This recipe packages KAuth 6.26.0 for HarmonyOS PC (OHOS aarch64, CMake project,
upstream project name `kauth`; KDE Frameworks 6).

## Source verification

- Official URL: `https://download.kde.org/stable/frameworks/6.26/kauth-6.26.0.tar.xz`
- SHA256 (verified on the downloaded tarball):
  `e6b6562114c2cb71db6ca48fdf0ebed2df70e164c48295b35433a80b03385847`

## Adaptations

- `KAUTH_BACKEND_NAME=FAKE` and `KAUTH_HELPER_BACKEND_NAME=FAKE` avoid unavailable
  Polkit and system D-Bus services.
- `KF_SKIP_PO_PROCESSING=ON` omits translation catalog generation.
- Dependencies are unified with two overrides (see "Dependency fixes" below).

No source patch is applied. Earlier revisions of this archive carried
`patches/0001-CMakeLists.txt.patch`, which disabled the whole `autotests/`
subdirectory with an early `return()` on OHOS, justified in this file as
"qdbusxml2cpp-generated DBus adaptor moc code is incompatible with the OHOS Qt
toolchain". **That justification was never verified and turns out to be
incorrect.** Two independent defects made the patch inert, so it never ran:

1. `conandata.yml` had no `patches:` section, so `export_conandata_patches()`
   exported nothing.
2. `build()` never called `apply_conandata_patches()`.

Because the patch never executed, it also could not have caused the observed
build failure. Once the two real dependency bugs below were fixed, all three
upstream autotest targets compiled and `KAuthSetupActionTest` passed with **no
patch at all**. The orphan patch and the duplicated nested `patches/patches/`
directory have been removed.

## First real failure and root causes

### 1. `KeyError: 'OHOS'` from the cmake tool_require (dependency bug)

```
cmake/4.4.3: Error in build() method, line 35
    get(self, **self.conan_data["sources"][self.version][str(self.settings.os)][arch],
    KeyError: 'OHOS'
```

`expat/2.8.2` (reached via `qtbase-sql-dbus` -> `dbus/1.14.10`) declares
`tool_requires("cmake/[>=3.17]")` when `Version(version) >= "2.7.4"`. The
conancenter-index cmake recipe distributes Kitware prebuilt binaries selected by
OS key, and its `conandata.yml` only lists `Linux`/`Macos`/`Windows`, so building
it for OHOS raises `KeyError: 'OHOS'`. With conancenter disabled the graph instead
fails earlier with `Package 'cmake/[>=3.17]' not resolved`. cmake is not published
on ohpcd at all, and hnp already provides cmake 4.1.2 on the profile PATH.

Fix: pin the ohpcd-adapted expat, which has no conan-side cmake tool_require:

```python
self.requires("expat/2.8.2.1", override=True)
```

(same approach as `avahi-tools`, `avahi-compat-libdns_sd`, `awf-gtk`).

### 2. `variable has incomplete type 'class Q_DBUS_EXPORT'` (header mixing)

After the cmake failure was resolved, the build failed compiling
`src/backends/dbus/DBusHelperProxy.h`:

```
include/QtDBus/qdbuserror.h:111:21: error: variable has incomplete type 'class Q_DBUS_EXPORT'
class Q_DBUS_EXPORT QDBusError {}; // dummy class for moc
src/backends/dbus/DBusHelperProxy.h:22:55: error: expected class name
src/backends/dbus/DBusHelperProxy.h:33:5: error: unknown type name 'QDBusConnection'
```

`kcoreaddons/6.26.0` references the plain `qtbase/6.11.1`, whose `qconfig.h`
defines `QT_NO_DBUS` (`QT_FEATURE_dbus -1`), while the QtDBus headers come from
`qtbase-sql-dbus/6.11.1`. `qdbuserror.h` therefore takes its
`#else` (no-D-Bus) branch, where `Q_DBUS_EXPORT` is never defined because
`qtdbusglobal.h` only includes `qtdbusexports.h` under `#ifndef QT_NO_DBUS`.

Fix: unify the graph on the D-Bus enabled base:

```python
self.requires("qtbase/6.11.1.1", override=True)
```

(same approach as `baloo/6.28.0` and `statusnotifieritem/6.26.0`; dependency
binaries remain cache hits under the override graph).

## Upstream tests

`autotests/CMakeLists.txt` declares 5 CTest entries when `BUILD_TESTING=ON`, but
`KAuthPolicyGenTest` and `KAuthPolicyGenTestCompare` are guarded by
`if(NOT "${KAUTH_BACKEND_NAME}" STREQUAL "FAKE")` and are therefore **not
registered** on OHOS (this recipe uses the FAKE backend). That leaves 3 registered
entries, all of which compiled and linked with no patch applied:

| Test | Result | Reason |
|------|--------|--------|
| `KAuthSetupActionTest` | **executed, passed 1/1 (100%)** | No session bus needed |
| `KAuthHelperTest` | excluded | Drives `DBusHelperProxy` over a D-Bus session bus |
| `KAuthFdTest` | excluded | Waits on a helper service registered on the session bus |

Measured run (`ctest --output-on-failure --no-tests=error -j1`, offscreen platform):

```
    Start 1: KAuthSetupActionTest
1/1 Test #1: KAuthSetupActionTest .............   Passed    0.08 sec
100% tests passed, 0 tests failed out of 1
```

Reported counts: discovered 5, registered 3, executed 1, passed 1, failed 0,
skipped 0, excluded 2, not_registered 2.

### Why the two helper tests are excluded

No `dbus-daemon` exists anywhere in this environment: not in the system paths,
not in the hnp toolchain, and not in any conan package. `dbus/1.14.10` on ohpcd
deliberately builds `target="dbus-1"` only ("daemon 在 OHOS 交叉编译下链接 expat
失败"), i.e. it ships `libdbus-1` and no daemon, and there is no `dbus-broker` or
`systemd` either. `KAuthFdTest` reaches this through a null
`QDBusConnection::sessionBus().interface()` (SIGSEGV), and `KAuthHelperTest`
blocks in the same class of session-bus wait.

The recipe probes for `dbus-daemon` at build time and starts a private session bus
when one is available; only when none can be found does it exclude these two
entries and report them as excluded. They are **not** counted as passing. This
follows the `akonadi/25.12.3` precedent for `dbus/1.14.10` environments.

## Build and test status

- `init-build` completed from the official KDE tarball; the recorded `BUILD_SYSTEM`
  was corrected from `autotools` to `cmake` (the value came from the URL-based
  guess in `init_build.py`, which falls back to `autotools` for KDE tarball URLs).
- `conan create kauth/6.26.0@ohpcd/stable` succeeds end to end (exit code 0):
  100% of targets built, the upstream `KAuthSetupActionTest` passes, and
  `test_package` builds and prints `PASS: KAuth action constructed OK`.
- `conan-verify` reports **Verdict: PASS** (G0, G1, G2, G3, G4, L2, L4, L5 all pass).

## HarmonyOS-specific test (rule12)

The external PR review (`pc-pr-review`) rule 12 requires every adapted package
to ship **at least one HarmonyOS-specific test**; a count of 0 fails with
`❌ FAIL 规则 12: 鸿蒙特有测试 N=0 < 1`. The PR description's "适配后测试用例
统计" table is what the reviewer reads, so the fix must land in the
`test_package` and be declared in its `MANIFEST.yml` at the same time.

kauth's HarmonyOS-specific test covers two layers, both driven from
`test_package/conanfile.py::test()` as separate `self.run(...)` calls:

### 1. Runtime layer - `test_package/test_kauth_ohos.cpp`

OHOS has no Polkit and no D-Bus session daemon, so the recipe builds kauth with
`KAUTH_BACKEND_NAME=FAKE` / `KAUTH_HELPER_BACKEND_NAME=FAKE`. Because no backend
plugin is installed under `KAUTH_BACKEND_PLUGIN_DIR`,
`BackendsManager::init()` falls back to a plain `FakeBackend`
(`src/BackendsManager.cpp`, `if (!auth) auth = new FakeBackend;`), which reports
`NoCapability`. The test asserts the resulting observable behavior of that
platform adaptation path:

| Assertion | Value on OHOS FAKE backend |
| --- | --- |
| `Action(name).name()` | round-trips |
| `Action(name).isValid()` | `true` (isValid() is purely "name is set") |
| `Action().isValid()` | `false` |
| `Action().status()` | `Action::InvalidStatus` (2) |
| `Action(name).status()` | `Action::DeniedStatus` (0) |
| `Action(name).execute()` -> `job->exec()` | `false` |
| `job->error()` | `ActionReply::BackendError` (9) |
| `job->errorString()` | "The backend does not specify how to authorize" |
| `helperId()` / `hasHelper()` | empty / `false` |
| `setDetailsV2()` / `detailsV2()` | round-trip |

The `BackendError` outcome is the **FAKE backend contract**, not a defect: with
`NoCapability`, `ExecuteJob` falls into its else branch
(`src/executejob.cpp`: `ActionReply r(ActionReply::BackendError); r.setErrorDescription(
tr("The backend does not specify how to authorize"));`) and reports the failure
through `KJob::setError()` / `setErrorText()`. This is exactly why kauth cannot
authorize on OHOS, and asserting it is a real gate on the adaptation.

The file starts with a `#ifndef __OHOS__ #error ... #endif` guard so a host
build cannot silently produce a meaningless "pass".

It needs only `QCoreApplication`: no session bus, no Polkit, no Qt platform
plugin. (A `QT_QPA_PLATFORM=offscreen` environment is still set by the recipe's
upstream test path but the binary does not depend on it.)

### 2. Artifact layer - `test_package/fixtures/ohos_artifact_check.py`

Verifies the FINAL conan package artifact `lib/libKF6AuthCore.a` using the
standard library only (no `readelf`/`llvm-ar` dependency):

1. the archive exists and is non-empty;
2. it is a real `ar` archive (`!<arch>\n`);
3. it has at least one member;
4. at least one member is an OHOS-shaped ELF relocatable object
   (ELF64, little-endian, `EM_AARCH64` = 183, `ET_REL` = 1);
5. no backend/helper plugin is shipped under `lib/plugins/kf6/kauth`, which is
   the precondition for the `FakeBackend` fallback the runtime test relies on.
   The compile-time plugin search path baked into `BackendsManager`
   (`KAUTH_BACKEND_PLUGIN_DIR`) is printed for auditability.

All checks fail closed (non-zero exit on the first failure).

### Correction carried in the same change

The previous `test()` built its runtime prefix as
`LD_PRELOAD=.../lib/libKF6AuthCore.so.6`. kauth 6.26.0 is packaged with
`shared=False`, so the package contains `libKF6AuthCore.a` and **no** `.so` —
the `LD_PRELOAD` target never existed (the loader silently ignored it, which is
why the old test still printed PASS). The prefix is now just
`LD_LIBRARY_PATH=<dependency lib dirs>`, matching what the static package
actually needs.
---

**编译结束**: 2026-09-20 10:41
**最终状态**: built
