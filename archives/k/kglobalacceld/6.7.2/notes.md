# kglobalacceld 6.7.2 notes

## Scope

First HarmonyOS PC (aarch64 / OHOS) adaptation of KDE Plasma's global
shortcut daemon kglobalacceld 6.7.2 (`libKGlobalAccelD.so` +
`kglobalacceld` daemon + `KGlobalAccelD` CMake package).
Upstream tarball: `kglobalacceld-6.7.2.tar.xz`,
sha256 `40cd6b417678faba69847e1fa4d9efc8f500cdf95db17e317d6d868d18c95339`
(https://download.kde.org/stable/plasma/6.7.2/).

The direct dependency KF6::GlobalAccel is the already-published
kglobalaccel/6.26.0 package (its notes.md covers the shared ecosystem
pitfalls: WITH_X11=OFF, qtbase-sql-dbus, SONAME flag, ECM_MODULE_PATH,
QT_ADDITIONAL_PACKAGES_PREFIX_PATH).

## Dependencies (R36, all verified consumable from ohpcd)

| dep | why | verified |
|---|---|---|
| kglobalaccel/6.26.0 | KF6::GlobalAccel is the PUBLIC link dep | CI graph + build |
| kconfig/6.26.0, kcoreaddons/6.26.0, kcrash/6.26.0, kwindowsystem/6.26.0, kservice/6.26.0 | PRIVATE link deps | CI graph + build |
| kdbusaddons/6.18.0 | KDBusService/KCrash for the daemon. **6.29.0 is unusable**: it requires qtbase/6.11.1.1, which conflicts with the qtbase/6.11.1 the whole published KF6 6.26 stack links (CI round 1: "Conflict between qtbase/6.11.1.1 and qtbase/6.11.1 ... originates from kdbusaddons/6.29.0"). 6.18.0 aligns on qtbase-sql-dbus/6.11.1 | CI graph + build |
| qtbase-sql-dbus/6.11.1 | only provider of Qt6::DBus (+ Qt6GuiPrivate) | CI graph + build |
| ecm/6.26.0 | build tool | CI graph + build |
| dbus/1.14.10.1 (tool) | dbus-daemon for the upstream-test session bus | CI graph + build |

**kjobwidgets / kio / KIOGui note (Coordinator question answered):** the
upstream PRIVATE deps `KF6::KIOGui` + `KF6::JobWidgets` are used only by the
desktop-file launch path in KServiceActionComponent. kjobwidgets/6.18.0 does
contain the used API (`KNotificationJobUiDelegate` etc.), but the real gap is
KIOGui: the published kio/6.26.0 is built `KIOCORE_ONLY` (its GUI closure
kconfigwidgets/kbookmarks/kcolorscheme/kjobwidgets are not published at
6.26), so `KF6::KIOGui` does not exist on ohpcd and no kjobwidgets version
choice can fix it. Patches 0001+0002 make KIO/JobWidgets optional
(`WITH_KIO` option, default ON upstream; OFF on OHOS) and compile the launch
path out with a `qCWarning` fallback. Shortcut registration, config
migration, the allow-list and the D-Bus service are unaffected. Upstream
already degrades the same way on Wayland sessions (main.cpp returns 0);
on OHOS there is additionally no key-grabbing backend (WITH_X11=OFF), so the
daemon is a build-level delivery: D-Bus service + config duties only.

## Adaptations (recipe layer + 5 minimal patches)

1. `WITH_X11=OFF` — OHOS Qt builds ship FEATURE_xcb/xlib=OFF and no
   `private/qtx11extras_p.h`; the xcb platform plugin and the GuiPrivate
   branch are compiled out (kglobalaccel 6.26.0 precedent).
2. `WITH_KIO=OFF` (patches 0001+0002, see above).
3. `KF6_MIN_VERSION 6.26.0 -> 6.18.0` (patch 0003) — only relaxes the
   kdbusaddons constraint; every other dep is published at >= 6.26.0
   (aurorae 6.7.2 / DRAFT-ohos-downstream-version-threshold-bump precedent).
4. Patch 0004 — **HMDFS is case-insensitive**: the library target
   `KGlobalAccelD` and the executable target `kglobalacceld` collide on
   `CMakeFiles/<target>.dir` / `<target>_autogen.dir`; the executable's
   AUTOMOC run overwrote the library's (empty HEADERS) and the
   `moc_*.cpp` files were never generated. The executable target is renamed
   to `kglobalacceld_daemon` with `OUTPUT_NAME kglobalacceld` preserved.
5. Patch 0005 — **E537 bare-name linking**: the published KF6 dependency
   packages ship SONAME-less .so, so linking their imported targets made lld
   record the absolute Conan cache paths into DT_NEEDED
   (`/storage/Users/currentUser/.conan2/p/...`, unrelocatable). The E537
   `IMPORTED_SONAME` stamping (method 1) had no effect on the link line
   (CI round 12), so the patch implements method 2: a
   `_ohos_link_kf6_bare()` helper links the SONAME-less KF6 deps via
   `target_link_directories` + bare `-l<name>` and re-adds the deps'
   INTERFACE_INCLUDE_DIRECTORIES, for both the library and the daemon
   target. Verified: lib and daemon DT_NEEDED are all bare basenames.
6. Recipe sets `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname,`
   (HarmonyOS has no CMake platform SONAME rule; kglobalaccel 6.26.0
   error #5 precedent) — libKGlobalAccelD.so.0 carries a proper DT_SONAME.
7. **Vendored shared `libdbus-1.so.3`**: the OHOS qtbase builds Qt6DBus
   with dbus-linked=OFF, so `libQt6DBus` dlopen()s `libdbus-1.so.3` at
   runtime — but the registry only ships STATIC `libdbus-1.a`
   (dbus/1.14.10*, 1.14.10.1, 1.14.10.2 all static-only). Without a shared
   libdbus every Qt6DBus consumer gets "DBus session bus not found"
   (invalid connection) and `KGlobalAccelD::init()` fails. The recipe
   builds the dbus-1 client shared library from the official dbus 1.14.10
   sources (fixed URL + sha256; NEEDED: libc only — no expat) and ships it
   in the package `lib/`. **Long-term fix: publish a shared-lib dbus
   package on ohpcd; afterwards this vendored copy can be dropped.**
8. `ECM_MODULE_PATH` + hand-written `conan_cmakedeps_paths.cmake`
   (qtbase cmake_find_mode=none), qtbase-sql-dbus first in CMAKE_PREFIX_PATH
   (kglobalaccel 6.26.0 precedent).
9. `BUILD_TESTING=ON`; the upstream autotests run on device inside build().

## Errors encountered (first error -> root cause -> fix)

| # | First error | Root cause | Fix |
|---|---|---|---|
| 1 | `Conflict between qtbase/6.11.1.1 and qtbase/6.11.1 ... originates from kdbusaddons/6.29.0` | kdbusaddons/6.29.0 requires qtbase/6.11.1.1; the rest of the KF6 6.26 stack requires qtbase/6.11.1 | require kdbusaddons/6.18.0 + patch 0003 (KF6_MIN_VERSION floor) |
| 2 | `make: jobserver mkfifo /storage/.../GMfifoNNNN: Operation not permitted` | the OHOS GNU make 4.4.1 port uses an mkfifo-based jobserver; the sandbox denies mkfifo everywhere (HMDFS EPERM, /tmp EROFS) | Ninja generator (recipe + test_package; attica-kf5 precedent) |
| 3 | `fatal error: 'moc_kglobalaccel_interface.cpp' file not found` | HMDFS case-insensitivity: `KGlobalAccelD_autogen` (lib) and `kglobalacceld_autogen` (exec) are the same physical directory; the exec's autogen (HEADERS=[]) overwrote the lib's | patch 0004 (rename exec target, OUTPUT_NAME kept) |
| 4 | test_package: `The following variables are used ... but they are set to NOTFOUND` / `KF6::GlobalAccel target was not found` | KGlobalAccelDConfig.cmake has no find_dependency(KF6GlobalAccel); upstream assumes consumers resolve it (kwin does) | test_package CMakeLists does find_package(KF6GlobalAccel) first |
| 5 | `kf.dbusaddons: DBus session bus not found` despite a live TCP bus | OHOS Qt6DBus dlopens `libdbus-1.so.3` at runtime; only static libdbus exists in the ecosystem | vendored shared libdbus-1 built in-recipe (see adaptation 7) |
| 6 | `absolute-path DT_NEEDED leak: [.../.conan2/p/kwind...]` | SONAME-less KF6 deps linked as imported targets -> absolute DT_NEEDED (E537) | patch 0005 bare-name linking; test_package asserts no absolute DT_NEEDED |
| 7 | `The plain signature for target_link_libraries has already been used` | CMake keyword/plain signature mix in patch 0005 helper | helper takes the scope keyword; daemon uses PRIVATE form |

## Upstream tests (R51 three-step declaration)

**Step 1 — inventory.** `autotests/` registers 3 ecm_add_test QtTest cases
when BUILD_TESTING=ON: `migrateconfigtest` (file-based config migration),
`shortcutstest` (registration/triggering through the dummy static platform
plugin), `allowlisttest` (allow-list gating through the daemon's D-Bus
service). Upstream CI requires them to pass on Linux/FreeBSD.

Function-level census (official PR-review convention: count QTest test
functions; `initTestCase`/`cleanupTestCase`/`_data` slots and parameterized
helper slots are not test functions): **6 test functions** —
`migrateconfigtest`: `testMigrate()`; `shortcutstest`: `testShortcuts()`
(15 data rows), `testSerialization()`, `testContestedKeys()`;
`allowlisttest`: `testAllowList()` (3 data rows),
`testAllowListMultipleActions()`. (The `_data`-fed parameterized rows are
distinct QVERIFY cases but one QTest test function; `compareGroups`/
`compareGroupList` in migrateconfigtest.cpp are parameterized helper slots,
not counted.)

**Step 2 — run (real machine, OHOS PC).** Executed inside the recipe's
build() (OS=OHOS guard) via
`ctest --test-dir <build> --output-on-failure --timeout 120`, with the
session bus started from the dbus/1.14.10.1 tool package
(`dbus-daemon --config-file session-tcp.conf --print-address --nofork`,
TCP + ANONYMOUS — the OHOS sandbox forbids AF_UNIX binds;
DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime) and the vendored
libdbus-1.so.3 on LD_LIBRARY_PATH.

```
1/3 Test #1: migrateconfigtest ................   Passed    0.11 sec
2/3 Test #2: shortcutstest ....................   Passed    1.03 sec
3/3 Test #3: allowlisttest ....................   Passed    0.53 sec
100% tests passed, 0 tests failed out of 3
```

(first all-green run: CI round 7 log
`/storage/Users/currentUser/tmp/oh-device-porting-v2/kglobalacceld-6.7.2-ci07.log`;
authoritative green run: round 15, same command. The D-Bus-driven tests were
NOT excluded — they run for real.)

**Function-level capture.** The two calibers are the same fact at different
granularity: 1 ctest executable = 1 group of QTest test functions, so the
executable-level "ctest 3/3 passed" above implies the function-level
"6/6 passed". Per-function PASS lines captured 2026-09-20 by re-running the
unmodified round-15 build tree with
`ctest -V --test-dir <build> --output-on-failure --timeout 120`
(recipe-equivalent env: offscreen QPA, recorded dep plugin/lib paths,
vendored libdbus, TCP+ANONYMOUS session bus; full log
`/storage/Users/currentUser/.local/state/oh-device-porting-v2/runs/kglobalacceld-6.7.2/evidence/upstream-test-functions-ci15.log`):

```
1: PASS   : MigrateConfigTest::testMigrate()
1: Totals: 3 passed, 0 failed, 0 skipped, 0 blacklisted, 31ms

2: PASS   : ShortcutsTest::testShortcuts(no mod)
2: PASS   : ShortcutsTest::testShortcuts(mod+key trigger)
2: PASS   : ShortcutsTest::testShortcuts(mods+key trigger)
2: PASS   : ShortcutsTest::testShortcuts(mods+key does not trigger mod+key)
2: PASS   : ShortcutsTest::testShortcuts(mod+key does not trigger mods+key)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only single mod)
2: PASS   : ShortcutsTest::testShortcuts(mod+key does not trigger modifier-only single mod)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only multiple mods)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only multiple mods trigger when released out of order)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only multiple mods does not trigger modifier-only single mod)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only multiple mods trigger when part of the sequence)
2: PASS   : ShortcutsTest::testShortcuts(modifier-only multiple mods trigger when any mod is released)
2: PASS   : ShortcutsTest::testShortcuts(mod+pointer does not trigger modifier-only single mod)
2: PASS   : ShortcutsTest::testShortcuts(mod+wheel does not trigger modifier-only single mod)
2: PASS   : ShortcutsTest::testShortcuts(mod+invalid does not trigger modifier-only single mod)
2: PASS   : ShortcutsTest::testSerialization()
2: PASS   : ShortcutsTest::testContestedKeys()
2: Totals: 19 passed, 0 failed, 0 skipped, 0 blacklisted, 883ms

3: PASS   : AllowListTest::testAllowList(allowlist disabled)
3: PASS   : AllowListTest::testAllowList(allowlist enabled, not listed)
3: PASS   : AllowListTest::testAllowList(allowlist enabled, listed)
3: PASS   : AllowListTest::testAllowListMultipleActions()
3: Totals: 6 passed, 0 failed, 0 skipped, 0 blacklisted, 443ms

100% tests passed, 0 tests failed out of 3
```

**Step 3 — report.** Executable caliber: 3 ctest executables, passed 3,
failed 0, skipped 0. Function caliber: 6 QTest test functions (Step 1
census), passed 6, failed 0, skipped 0.

## test_package

- `test_ohos_daemon` (new OHOS-specific consumer test, 7 assertions): links
  K::KGlobalAccelD via the exported CMake package, runs `KGlobalAccelD::init()`
  against the TCP+ANONYMOUS session bus shim, asserts the daemon owns
  `org.kde.kglobalaccel` and exposes `/kglobalaccel` with no platform grabber
  plugin (WITH_X11=OFF), and verifies clean tear-down (second init cycle).
- `_elf_artifact_checks` (new OHOS-specific artifact assertions): packaged
  `libKGlobalAccelD.so` carries `DT_SONAME libKGlobalAccelD.so.0`; DT_NEEDED
  contains no `libKF6KIO*`/`libKF6JobWidgets*` (WITH_KIO=OFF effective) nor
  `libxcb*`/`libX11*` (WITH_X11=OFF effective) and no absolute Conan cache
  paths (E537); the `kglobalacceld` daemon binary exists; the xcb platform
  plugin directory is absent.

## Verification

```
CI_PACKAGES=archives/k/kglobalacceld/6.7.2  ci/conan/build_and_test.sh archives/k/kglobalacceld/6.7.2
L0 pass / L1 pass (upstream tests + test_package executed) / L2 skip (daemon --version needs a bus+QPA, non-blocking)
L4 warn (grep false positive on patch text, non-blocking) / L5 pass
Pass rate: 100.0% (1/1)
```
Log: `/storage/Users/currentUser/tmp/oh-device-porting-v2/kglobalacceld-6.7.2-ci15.log`
(final green run; earlier rounds ci01-ci14 document each error above).

Package contents: `include/KGlobalAccelD/`, `lib/libKGlobalAccelD.so.0` +
`.so.6.7.2` (+ exported `lib/cmake/KGlobalAccelD/`), `lib/libdbus-1.so.3`
(vendored shared client), `bin/kglobalacceld` (libexec resolved to bin on
this platform), systemd user unit + XDG autostart desktop data files,
logging categories. `readelf -d libKGlobalAccelD.so.0`: SONAME
`libKGlobalAccelD.so.0`, NEEDED all bare basenames.

## Caveats / partial-adaptation signals (for Curator)

- **No key grabbing**: WITH_X11=OFF and no platform grabber backend on OHOS;
  shortcuts can be registered/migrated/allow-listed and served over D-Bus,
  but nothing fires them (upstream is likewise a no-op grabber on Wayland).
- **No KIO launch path**: WITH_KIO=OFF; desktop-file launch on shortcut
  activation logs a warning and does nothing (KIOGui unpublished; see
  dependency table). `blocker:依赖链断裂` signal.
- **Vendored libdbus-1.so.3**: runtime-level ecosystem gap (Qt6DBus dlopen
  vs static-only registry); recommend a shared dbus package on ohpcd.
- **HMDFS case-insensitivity** (patch 0004) and **make mkfifo jobserver**
  (Ninja) are new cross-library platform findings worth curation.
- Runtime D-Bus needs the TCP+ANONYMOUS session-bus shim; a real OHOS
  session would need AF_UNIX permissions or the shim.
