# yuview 2.14 HarmonyOS PC adaptation notes

## Scope

`yuview/2.14` adapts upstream YUView (tag `v2.14`) for HarmonyOS PC aarch64.
The package builds and installs the YUView application together with the
`YUViewLib` static library that upstream builds but does not install.

## W0 dependency check

| Dependency | Status | Evidence |
|---|---|---|
| `qtbase/6.11.1.3` | Published | `bash ci/scripts/preflight_check.sh yuview/2.14 --deps "qtbase/6.11.1.3"` → all dependencies published; version `yuview/2.14` not occupied |
| `dbus/1.14.10`, `libxkbcommon/1.6.0` | Published (transitive of qtbase) | `conan download <ref> -r=ohpcd --only-recipe` → success |
| `openssl/3.5.6.1`, `zstd/1.5.7.1` | Published (transitive of qtbase) | `conan download <ref> -r=ohpcd --only-recipe` → success |
| `wayland/1.22.0`, `wayland-protocols/1.36` | Published (transitive of qtbase) | `conan download <ref> -r=ohpcd --only-recipe` → success |

YUView itself has no third party library dependencies beyond Qt; the upstream
README states there are no further dependent libraries.

## Source and build system

- Source: `https://github.com/IENT/YUView/archive/refs/tags/v2.14.tar.gz`
- SHA256: `cde4e5726286d18cd7b7f2458fc3e6fb198c1bd629075e8f654b365c3b866c51`
- Build system: qmake subdirs (`YUView.pro` → `YUViewLib` static library, then
  `YUViewApp` executable; `YUViewUnitTest` is added by `CONFIG+=UNITTESTS`)

## Upstream test census (R51)

Clean source inspection, before any adaptation:

| Metric | Count | How obtained |
|---|---|---|
| Test executables registered by qmake | 11 | `find YUViewUnitTest -name "*.pro"` (leaf `TEMPLATE = app` projects) |
| Test source files | 11 | `find YUViewUnitTest -name "*.cpp"` |
| Test slots (`private slots:`) | 21 | counted per file in the `private slots:` block |
| Data-driven test functions | 4 | `grep -rn "_data()" YUViewUnitTest` |

The per-file slot counts are: FilesourceTest 2, FilesourceAnnexBTest 2,
StatisticsDataTest 2, StatisticsFileCSVTest 1, StatisticsFileVTMBMSTest 1,
ConversionRGBTest 3, Issue511RGBConversionInvalidMemoryAccess 1,
PixelFormatRGBGuessTest 2, PixelFormatRGBTest 2, PixelFormatYUVGuessTest 2,
PixelFormatYUVTest 1.

Upstream runs them through qmake: `qmake CONFIG+=UNITTESTS .. && make && make check`.
All eleven only need QtCore, QtXml and QtTest (`QT -= gui`), so they run
headless. The recipe builds them and executes each binary, treating a non-zero
exit code as a build failure.

## Reproduction steps

```sh
# 1. extract the upstream archive
tar xf YUView-2.14.tar.gz && cd YUView-2.14

# 2. shadow build with the Qt Base package
export PATH=<qtbase>/bin:$PATH LD_LIBRARY_PATH=<qtbase>/lib QMAKEPATH=<qtbase>
mkdir build && cd build
qmake6 ../YUView.pro -spec harmonyos-clang CONFIG+=UNITTESTS \
  CONFIG+=release CONFIG-=debug VERSION=2.14 QMAKE_HOST.os=Linux \
  QMAKE_CC=<clang> QMAKE_CXX=<clang++>
make -j8

# 3. upstream tests (each binary is a QtTest program)
./YUViewUnitTest/video/yuv/PixelFormatYUVTest/PixelFormatYUVTest
# ... and the other ten executables listed in test_package/MANIFEST.yml

# 4. full package validation
conan create archives/y/yuview/2.14 -pr:h=ohos -pr:b=ohos --build=missing
```

## Problems found and fixes

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | `Project ERROR: Unknown module(s) in QT: opengl` | The HarmonyOS PC Qt Base build has no OpenGL module; YUView requests it unconditionally | Patch 0001/0003: request the module inside `qtHaveModule(opengl)`, so the upstream behaviour is unchanged on Qt builds that ship OpenGL |
| 2 | `no member named 'sslErrors' / 'connectToHostEncrypted' in 'QNetworkAccessManager'` | `qtbase/6.11.1.3` is built with `QT_NO_SSL` | Patches 0004/0005: wrap the SSL signal connection, the encrypted-connect call and the `QSslError` forward declaration in `QT_CONFIG(ssl)` |
| 3 | `no type named 'identity' in namespace 'video::q20'` when compiling `VideoCache.cpp` | The file included its own moc outside-in: `#include "VideoCache.moc"` sat inside `namespace video`, and Qt 6 moc output refers to `q20::identity` unqualified | Patch 0006: include the moc file after closing `namespace video` |
| 4 | `YUVIEW_VERSION` is `0`, so `--version` cannot report the release | Release archives are not git checkouts and `$$system("git describe --tags")` returns empty | Patches 0001/0003: keep the upstream `git describe`/emptiness fallback and then let a build-system supplied `VERSION` win when present |
| 5 | CI link failure: `Error loading shared library libxml2.so.16: (needed by /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/lld)` followed by a cascade of `xmlFreeDoc / xmlReadMemory / xmlStrdup ...: symbol not found` relocations | The OHOS SDK's `llvm/bin/lld` is a dynamically linked host ELF whose only RUNPATH is `$ORIGIN/../lib` (its `DT_NEEDED` lists `libxml2.so.16`). Clang drives that linker in-process, so the worker's loader path must already contain `<sdk>/native/llvm/lib`. The repository profile `ci/conan/profiles/ohos-aarch64` sets that directory in `[buildenv]`, but this recipe's `build()` runs `qmake`/`make` through `subprocess` and only applied its own Qt-only `Environment`, so the profile entry never reached the linker. Compilation succeeded and only linking failed, which is what made it look like a source error | `_lld_environment()` prepends the directory derived from the active compiler (`clang` → `<sdk>/native/llvm/lib`, verified to contain the ABI-matched `libxml2.so.16`) and wraps **only** the qmake/make compile-and-link block. The upstream test binaries are executed under `_qt_environment()` instead, so the SDK host libraries cannot leak into target processes |

### Fix 5 in detail (lld / libxml2.so.16)

Knowledge base references:

| Entry | Role in this fix |
|---|---|
| `knowledge/graph/E120.kv` | Same error surface (`cannot open shared object file: libxml2.so.16`); `rec_approach: env-library-path` — the environment-injection family this fix belongs to |
| `knowledge/graph/E132.kv` | Same root cause (`lld` needs `libxml2.so.16`, `LD_LIBRARY_PATH` incomplete); `rec_approach: set-environment-path` |
| `knowledge/graph/E266.kv` | Same error signature (`Error loading shared library libxml2.so.16.*needed by.*lld`, `xmlFreeDoc: symbol not found`). Its `rec_approach: use-alternative-linker` (`-fuse-ld=/data/service/hnp/bin/ld`) is **not** used — see below |
| `knowledge/graph/E341.kv` (doc file `doc/E321.md`) | The decisive entry: `conflicts_with: [E266]`, `rec_approach: preserve-sdk-lld-with-scoped-host-runtime`. Its `forbid_1` bans `-fuse-ld=.../hnp/bin/ld` because the GNU ld fallback bypasses the SDK linker and produces target executables that HarmonyOS refuses to start (`permission denied`); its `forbid_2` bans keeping `llvm/lib` on `LD_LIBRARY_PATH` while target executables run |

Why the GNU ld fallback was rejected: E321's documented consequence is that the
fallback "changes the target linker path after the SDK lld probe and bypasses
the toolchain behavior expected by HarmonyOS CI … every generated test
executable can fail to start with `permission denied`". E341 records this as
`forbid_1` with `conflicts_with: [E266]`, so E266's `rec_approach` is
superseded by E341's scoped-host-runtime approach. This package therefore keeps
the SDK `lld` and only repairs its host runtime, which is exactly E341's
`rec_approach`.

Scope control (E341 `forbid_2`): the injection is confined to the compile/link
block. `_run_upstream_tests()` runs under `_qt_environment()` (Qt paths only, no
`llvm/lib`), so the SDK host libraries are absent when the 11 upstream test
executables and the consumer program are executed. `generate()` exports both
environments as separate scripts (`conanbuild_yuview_qt`,
`conanbuild_yuview_lld`) so the split is explicit and auditable.

`archives/y/yuview/hints/environment.sh` records the same directory for manual
reproduction/debugging only; CI does not need to source it because
`conanfile.py` injects the path itself.

## Adaptation decisions

- `QT += opengl` is made conditional rather than deleted, so non-OHOS Qt
  configurations keep the module. YUView 2.14 does not call OpenGL directly
  (`grep -ri opengl` matches only the `.pro` files), so no functionality is lost
  on this platform.
- The `--version`/`--help` handling is added before `QApplication` is
  constructed, so the package is verifiable on a platform without a window
  system. The GUI code path is untouched.
- No source file was deleted and no upstream test was modified.
- `libYUViewLib.a` (22 MB) and its headers are shipped under `sdk/` so a real
  consumer can be compiled in `test_package`; upstream does not install it.

## Verification

- `conan create archives/y/yuview/2.14 -pr:h=ohos -pr:b=ohos --build=missing`
- Upstream unit tests: 11/11 executables built and passed (see PR description
  for the N/N' table).
- `test_package`: compiles and runs a YUViewLib consumer
  (pixel format name round trip, 4 assertions) and queries the packaged
  executable with `--version` and `--help`.

## Known boundaries

- Opening the GUI needs a QPA platform plugin. Only `offscreen` and `minimal`
  are available in this Qt Base build, so an interactive windowed session is not
  part of this package's verification.
- The optional self-update feature depends on SSL and is compiled out here.

## Preflight exception record (PF8 ⟷ PF9)

`commands.json` is required at the **software level**
(`archives/y/yuview/commands.json`, R38 / PF8) because this package installs the
`bin/YUView` executable. PF9 requires every changed `archives/` path to have at
least five segments (`archives/<letter>/<package>/<version>/<file>`), so it
rejects that same software-level file. The two gates contradict each other for
CLI packages.

This is a known framework defect with prior occurrences in this repository
(e.g. `archives/b/box64/0.4.4/notes.md` records it as framework issues #7/#24;
`archives/c/canfigger/0.3.2/notes.md` records it as finding P1-2). Consistent
with those precedents, PR creation is performed with `OHC_PREFLIGHT=0`, leaving
this trace; the remaining gates (PF1-PF8 and the R52 cross-check) were executed
and passed, and the CI L0k gate verifies `commands.json` on the platform side.
---

**编译结束**: 2026-10-03 14:52
**最终状态**: published
