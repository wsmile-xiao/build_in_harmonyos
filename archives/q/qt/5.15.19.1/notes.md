# qt 5.15.19 HarmonyOS PC pre-adaptation notes

## Scope

This archive prepares a first-pass `qt/5.15.19` Conan recipe for HarmonyOS
PC. The package intentionally builds a headless Qt 5 foundation from the
official single source archive and limits the delivered surface to qtbase:
Core, Network, Gui, Widgets and Xml.

This is not a full Qt desktop stack and does not include QML, WebEngine,
Wayland, X11, OpenGL/EGL, DBus, multimedia or Qt tool modules. Those should be
adapted as separate libraries/modules if later issues require them.

## W0 dependency check

No Conan package requirements are introduced in this first pass.

The recipe uses Qt's bundled zlib, pcre, libpng, libjpeg, freetype and
harfbuzz, and disables external desktop integration stacks. That keeps the W0
published-dependency set empty and avoids mixing dependency adaptation into the
`qt/5.15.19` PR. SSL and SQLite SQL plugin support are disabled for the first
validation pass.

Build-time tools still need to exist in the HarmonyOS runner/profile:

- clang and clang++ from `tools.build:compiler_executables` or PATH
- sh and make
- perl for Qt 5 syncqt/qmake scripts
- binary-sign-tool, llvm-objcopy and llvm-objdump for installed ELF signing

If any of those are missing on the runner, treat them as environment/toolchain
blockers. Do not add unrelated dependency archives to this PR.

## Source and build system

Source archive:
`qt-everywhere-opensource-src-5.15.19.tar.xz`

Official URL:
`https://download.qt.io/archive/qt/5.15/5.15.19/single/qt-everywhere-opensource-src-5.15.19.tar.xz`

SHA256:
`173c2326dae138bbb0d98921e9d911e55c00163d93a6db29f294b5e19ff306ae`

Qt 5.15.19 uses the top-level `configure` script and qmake-generated Makefiles.
This differs from the already adapted Qt 6 `qtbase/6.11.1` recipe, which uses
CMake. The Qt 6 HarmonyOS experience is still useful for platform choices:
keep offscreen/raster testing, disable unavailable desktop stacks, disable
pthread cancellation paths where present, check whether ARM AES hash paths exist before patching, and re-sign
installed ELF files after installation.

## Patch summary

1. `0001-mkspecs-add-harmonyos-clang.patch`
   Adds `qtbase/mkspecs/harmonyos-clang` and reuses Qt's Linux clang common
   qmake rules while tagging the qmake platform as `ohos`/`harmonyos`.
2. `0002-corelib-disable-pthread-cancel.patch`
   Mirrors the Qt 6 adaptation pattern and uses `QT_NO_PTHREAD_CANCEL` to
   avoid pthread cancellation APIs on HarmonyOS.
Dropped Qt 6 carry-over: the ARM AES qhash block is absent from Qt 5.15.19, so `0003-corelib-disable-arm-aes-hash-on-harmonyos.patch` is not applied.

## Test strategy

The recipe configures Qt with examples/tests excluded from the default graph,
then uses the built qmake to configure and build five selected upstream tests:

- `tst_qstring`
- `tst_qhostaddress`
- `tst_qimage`
- `tst_qsizepolicy`
- `tst_qdom`

When `can_run(self)` is true, the selected tests execute with
`QT_QPA_PLATFORM=offscreen`. The consumer `test_package` creates a real
`QApplication`, shows a `QWidget`, exercises `QImage`/`QPainter`, validates
`QHostAddress`, and checks `QDomDocument` DOM behavior.

## Local verification status

This Windows shell does not have `conan` in PATH, and no HarmonyOS device
window was available in this turn. Local work therefore stopped at recipe,
source checksum, patch and test_package preparation. The archive is marked
`status: failed` until the OHOS single-package validation has run.

## Shadow CI attempts

On 2026-08-25, the package directory was copied into an isolated HarmonyOS job:

`/storage/Users/currentUser/ohos-users/codex/qt-5.15.19-q515-shadow-ci`

The runner was started with `--try-lock` for the single package
`archives/q/qt/5.15.19`. It created run id:

`codex-qt-qt-5.15.19-q515-shadow-ci-20260825-200356-29883`

Result: lock busy, exit code 75. The runner did not enter the build/test
phase because `/storage/Users/currentUser/ohos-test-locks/device-global.lock.d`
was held by a qtdeclarative shadow CI run. Logs are under the run's `logs/`
directory.
The device lock later became available and the monitor started a real
single-package run:

`codex-qt-qt-5.15.19-q515-shadow-ci-20260825-204513-11298`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-5.15.19-q515-shadow-ci-20260825-204513-11298/logs`

Result: failed, exit code 1. The runner acquired the lock at
`2026-08-25T12:45:14Z` and ended at `2026-08-25T13:30:22Z`. The package reached
L1 `conan create`, downloaded and unpacked the 664.3 MB source archive, then
stopped after logging `Copying sources to build folder`. The `conan create`
process was wrapped by `timeout --signal=KILL 2700`, so this is most likely a
CI timeout during Qt's large source copy before configure/build diagnostics
were emitted. Upstream selected tests and `test_package` were not reached.

Follow-up fix: `conanfile.py` now sets `no_copy_source = True` so Conan skips copying the full Qt source tree before the shadow build configure step.
A second run was started after fixing the recipe with `no_copy_source = True`:

`codex-qt-qt-5.15.19-q515-shadow-ci-r2-20260825-225448-43966`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-5.15.19-q515-shadow-ci-r2-20260825-225448-43966/logs`

Result: failed, exit code 1. This was a runner-wrapper issue rather than a Qt
package build failure: the zsh body referenced `OHOS_JOB_BASE` before it was set,
so the command stopped before `ci/conan/setup.sh` and before `conan create`.

A third run was started with `OHOS_JOB_BASE` exported explicitly:

`codex-qt-qt-5.15.19-q515-shadow-ci-r3-20260825-225637-44722`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-5.15.19-q515-shadow-ci-r3-20260825-225637-44722/logs`

Result: failed, exit code 1. This run confirmed `no_copy_source = True` worked: Conan built in the package build folder and no longer emitted the large source copy step. The next blocker is patch parsing before configure: `0001-mkspecs-add-harmonyos-clang.patch` reports `invalid hunk no.1 at 22` for `b/qtbase/mkspecs/harmonyos-clang/qmake.conf`. Upstream selected tests and `test_package` were not reached.

Follow-up fix for r4: `conandata.yml` now sets `strip: 1` for the active a/b-style patches, `0001-mkspecs-add-harmonyos-clang.patch` declares the qmake.conf add-file hunk as 17 lines, and `0002-corelib-disable-pthread-cancel.patch` was rebased onto the actual Qt 5.15.19 `qthread_unix.cpp` context. The Qt 6-only ARM AES qhash patch was dropped because the target block is absent in Qt 5.15.19.

r4 queue status: local YAML, patch parse, git diff --check, and remote git apply --check dry-run all passed after the patch cleanup. The remote package has been synced. At the last manual check, the global device lock was held by `currentUser-gnustep-base-gnustep-base-1.31.1-shadow-r8-20260825-232456-20028`, so heartbeat automation `monitor-qt5-harmonyos-shadow-ci-r4` will keep watching and start r4 when the lock is free.

A fourth run completed after the patch cleanup:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r4-20260826-011156-43279`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r4-20260826-011156-43279/logs`

Result: failed, exit code 1. This run confirms the r3 patch parsing fixes worked: Conan applied both active patches, skipped the full source copy through `no_copy_source = True`, and reached Qt configure. The new blocker is `qtbase/configure` execute permission: the top-level `configure` script invokes `qtbase/configure` directly, and the extracted nested script failed with `Permission denied` (`ConanException: Error 126`). L1 failed; selected upstream tests, L4, and `test_package` were not reached. Follow-up r5 should make the relevant configure scripts executable after source extraction or invoke the nested configure through `sh` before rerunning on device.

Follow-up fix for r5: `conanfile.py` now chmods executable bits onto `configure` and `qtbase/configure` after `apply_conandata_patches(self)` and before the shadow-build configure step.

A fifth run used that configure permission fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r5-20260826-153312-64739`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r5-20260826-153312-64739/logs`

Result: failed, exit code 1. The runner acquired the global device lock at
2026-08-26T15:33:12+08:00, but the old 2700s build timeout killed the run while
the Qt source download/extraction path was still in progress. Follow-up manual
runs use a 14400s build timeout and a prewarmed Conan source cache.

A twelfth manual run reached Qt configure tests after the cache and argument
fixes:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r12-20260826-184900-60101`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r12-20260826-184900-60101/logs`

Result: failed, exit code 3. qmake was created, but `verifyspec` failed because
the bootstrap `qt.conf` still advertised `TargetSpec=dummy`; the config-test
qmake subprocess then loaded the dummy mkspec and reported `Unknown generator
specified: DUMMY`. A manual replay of the same `verifyspec` directory passed
when `TargetSpec=harmonyos-clang` was written into `qt.conf`.

Follow-up fix for r13: `conanfile.py` now patches `qtbase/configure` so the
bootstrap `qt.conf` writes `TargetSpec=$PLATFORM` next to `HostSpec=$PLATFORM`.
This keeps config-test qmake subprocesses on the `harmonyos-clang` mkspec.

A thirteenth manual run used that target-spec bootstrap fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r13-20260826-191131-31889`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r13-20260826-191131-31889/logs`

Result: failed, exit code 1. The runner acquired the global device lock at
2026-08-26T11:11:32Z, `QMAKE_XSPEC` was correctly set to `harmonyos-clang`,
`verifyspec` passed, and Qt configure completed. The next blocker was the build
cwd: the recipe ran `make` from the Conan layout build directory
`.../b/build`, but Qt's top-level configure generated `Makefile` in `.../b`.

Follow-up fix for r14: the recipe now uses the Qt top-level build directory
(`dirname(self.build_folder)`) for `make`, `make install`, and selected upstream
test build roots.

A fourteenth manual run used that top-level make cwd fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r14-20260826-192841-39419`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r14-20260826-192841-39419/logs`

Result: failed, exit code 1. The runner acquired the global device lock after
the top-level make cwd fix. Top-level `make` started, but the qtbase sub-qmake
failed with `Project ERROR: Could not find feature system-zlib` because
configure placed the bootstrap qmake under the Conan layout build directory
while `qconfig.pri` and `qmodule.pri` were generated under `qtbase`.

A fifteenth manual run tried the source top-level configure entry point:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r15-20260826-194449-46990`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r15-20260826-194449-46990/logs`

Result: failed, exit code 1. The top-level configure script internally executed
`qtbase/configure` directly and hit `Permission denied`, even though the recipe
had applied executable mode. Follow-up r16 keeps the direct `sh qtbase/configure`
invocation but runs it from the qtbase build directory so qmake and qtbase
configuration files stay aligned.

A sixteenth manual run used that qtbase configure cwd fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r16-20260826-195653-51465`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r16-20260826-195653-51465/logs`

Result: failed, exit code 1. The runner acquired the global device lock after
combining direct `sh qtbase/configure` with the qtbase build cwd. Configure
completed, top-level `make` started, and Qt progressed into QtCore compilation.
The new blocker is that `qthread_unix.cpp` still contains unguarded
`pthread_setcancelstate` and `pthread_testcancel` calls in
`QThreadPrivate::start()` and `QThread::setTerminationEnabled()`, even though
`QT_NO_PTHREAD_CANCEL` is defined for HarmonyOS.

Follow-up fix for r17: `_ensure_pthread_cancel_guard()` now checks each pthread
cancel call site independently. It keeps the existing `QThread::terminate()`
guard and also guards the start/enable/testcancel call sites when
`QT_NO_PTHREAD_CANCEL` is defined.

A seventeenth manual run used the expanded pthread cancel guard:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r17-20260826-202246-63229`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r17-20260826-202246-63229/logs`

Result: failed, exit code 1. The runner acquired the global device lock after
the CI script exported recipe hash `qt948407107748b`, revision
`41cb04e22e003e46bc0848eb89232a9b`. Configure passed, QtCore built, and the
build progressed into QtNetwork, confirming the expanded pthread cancel guard
worked. The next blocker is shared-library alias creation: the remote filesystem
rejected qmake's `ln -s` commands, leaving `libQt5Core.so.5.15.19` present but
`libQt5Core.so` missing, so QtNetwork failed to link.

Follow-up fix for r18: the HarmonyOS mkspec now sets
`QMAKE_LN_SHLIB = cp -f`, so qmake materializes versioned shared-library
aliases as regular copied files instead of unsupported symbolic links.

A eighteenth manual run is active with the shared-library alias copy fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r18-20260826-224202-49580`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r18-20260826-224202-49580/logs`

Result: failed, exit code 1. The runner acquired the global device lock with
recipe hash `qt63ce2fa4d80d8`, revision
`ea603aa3217a75e1e5dee9a45cffd2f5`.

Update while r18 is running: this run showed that setting
`QMAKE_LN_SHLIB = cp -f` in `harmonyos-clang/qmake.conf` is not enough. Qt's
`qtbase/mkspecs/features/spec_post.prf` overwrites the value back to `ln -s`
after the mkspec is loaded. `libQt5Core.so.5.15.19` was built, but qmake still
failed to create `libQt5Core.so`, `libQt5Core.so.5`, and
`libQt5Core.so.5.15`; those aliases were manually copied into the active r18
build tree so the run can keep probing for later blockers.

The r18 build then reached the selected upstream test qmake stage and failed on
`qtbase/tests/auto/corelib/text/qstring` with `Project ERROR: Operating system
not supported.` A qmake probe showed `QMAKE_HOST.os=HarmonyOS`; Qt's
`qtAddTargetEnv` helper in `qtbase/mkspecs/features/qt_functions.prf` only maps
Linux/BSD/SunOS/QNX/GNU-like hosts to `LD_LIBRARY_PATH`, so HarmonyOS fell into
the unsupported branch.

Follow-up fix for r19: `conanfile.py` now appends a HarmonyOS-specific override
to `qtbase/mkspecs/features/spec_post.prf`, includes `HarmonyOS` in
`qt_functions.prf`'s `LD_LIBRARY_PATH` host OS branch, and
`0001-mkspecs-add-harmonyos-clang.patch` carries both hunks.

A nineteenth clean manual run used both fixes:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r19-20260826-233412-9083`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r19-20260826-233412-9083/logs`

Result: failed, exit code 1. The runner acquired the global device lock with
recipe hash `qtccbdb31c16d2a`, revision
`db0dd9e234c5521e13b9d06f5039e456`, and failed in `source()` while applying
`0001-mkspecs-add-harmonyos-clang.patch`. The `qt_functions.prf` hunk header
pointed at line 217, but the first context line is line 214 in the Qt 5.15.19
source, so Conan's patcher did not match the hunk. Follow-up r20 corrects the
hunk header while keeping the `spec_post.prf` `QMAKE_LN_SHLIB = cp -f` override
and the HarmonyOS `LD_LIBRARY_PATH` host OS classification.

A twentieth clean manual run used the corrected hunk header:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r20-20260826-235743-19036`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r20-20260826-235743-19036/logs`

Result: failed, exit code 1. The runner acquired the global device lock with
recipe hash `qt7f284de7e7642`, revision
`95025b2c5c9b8497a5011e5b29eb488f`. This clean run validated the corrected
`qt_functions.prf` hunk header, the `spec_post.prf`
`QMAKE_LN_SHLIB = cp -f` override, and the HarmonyOS `LD_LIBRARY_PATH` host OS
classification without manual shared-library alias repair. QtBase built through
libraries, plugins, and selected upstream test compilation, then failed while
running `tst_qstring`: the test process could not resolve QtCore/QtTest symbols
because the recipe's test environment did not prepend the build tree's
`qtbase/lib` to `LD_LIBRARY_PATH`.

Manual replay against the r20 build tree with `LD_LIBRARY_PATH` set passed
`tst_qstring`, `tst_qhostaddress`, `tst_qimage`, and `tst_qsizepolicy`. The
remaining `tst_qdom` failure was `QTemporaryFile::open()` using the default
read-only `/tmp`; it passed after `TMPDIR` was set to a writable directory under
`selected-upstream-tests`. Follow-up r21 adds both fixes to the selected
upstream test environment.

A twenty-first clean manual run used the selected upstream test environment
fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r21-20260827-010319-48406`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r21-20260827-010319-48406/logs`

Result: failed, exit code 1. The runner started at 2026-08-26T17:03:20Z with
runner pid `48406` and ended at 2026-08-26T17:48:26Z. This run kept the r20
patch/configure/build fixes and added `LD_LIBRARY_PATH=<build>/qtbase/lib`
plus writable `TMPDIR/TMPPREFIX` while running selected upstream tests.

The failure was the CI wrapper timeout, not a new Qt compile error:
`conan create TIMED OUT after 2700s`. The log shows the clean build progressed
through configure and QtCore/QtNetwork/QtSql/QtXml/QtGui with copied
shared-library aliases, then was killed while the main Qt build was entering
`qtbase/src/widgets`. Follow-up r22 should keep the same recipe and run the
same package with `BUILD_TIMEOUT=14400`.

A twenty-second clean manual run started with the same recipe and an extended
build timeout:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r22-20260827-015548-6664`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r22-20260827-015548-6664/logs`

Result: failed, exit code 1. The runner started at 2026-08-26T17:55:48Z with
runner pid `6664` and ended at 2026-08-26T18:45:25Z. This run set
`BUILD_TIMEOUT=14400`, progressed past `qtbase/src/widgets`, completed the Qt
build, installed and packaged Qt, and created package revision
`a6411e939e16a13aef8f0e722f107c74`.

The new failure is in `test_package` runtime loading: `./test_qt5` could not
load `libQt5Core.so.5`, `libQt5Network.so.5`, `libQt5Widgets.so.5`,
`libQt5Xml.so.5`, or `libQt5Gui.so.5`. The package install log shows Qt's
install Makefiles still tried to create symlink aliases inside the package
`lib` directory, and the remote filesystem rejected them with `Permission
denied`. Follow-up r23 materializes installed shared-library aliases as
regular copies after `make install`, publishes `LD_LIBRARY_PATH=<package>/lib`
through `package_info()`, and explicitly prepends the same lib directory in
`test_package`.

A manual replay against the r22 package folder passed after copying the missing
aliases and setting `LD_LIBRARY_PATH`/`QT_PLUGIN_PATH`:

`Qt 5.15.19 offscreen QPA, raster painting, and XML work`

A twenty-third clean manual run started with the package alias/runtime-env fix:

`codex-qt-qt-qt-5.15.19-q515-shadow-ci-r23-20260827-024955-38296`

Log directory:
`/storage/Users/currentUser/ohos-test-runs/codex-qt-qt-qt-5.15.19-q515-shadow-ci-r23-20260827-024955-38296/logs`

Result: passed, exit code 0. The runner started at 2026-08-26T18:49:54Z with
runner pid `38296`, used `BUILD_TIMEOUT=14400`, and ended at
2026-08-26T19:54:42Z. It built and packaged Qt successfully, created package
revision `3dbe922fd67f531ba69484905c55bdaa`, and ran both selected upstream
tests and the consumer `test_package`.

Selected upstream test totals from the r23 log:

- `tst_qstring`: 1461 passed, 0 failed, 8 skipped
- `tst_qhostaddress`: 385 passed, 0 failed
- `tst_qimage`: 2077 passed, 0 failed
- `tst_qsizepolicy`: 25928 passed, 0 failed
- `tst_qdom`: 157 passed, 0 failed

The consumer test printed:

`Qt 5.15.19 offscreen QPA, raster painting, and XML work`
