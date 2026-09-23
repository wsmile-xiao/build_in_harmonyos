# qtbase 6.11.1.2 — HarmonyOS PC

## Source and scope

The upstream source is Qt Base 6.11.1, tag `v6.11.1`, commit
`59c81a3c2247b821b9b84b4eb8d939b77e07e276`. `6.11.1.2` is the Conan
adaptation revision. The official 50,648,500-byte source archive has SHA256
`d9594a31228aa23ad6b531719a29b45f0f3989fe6c136d45767ea179f233c1ac`.

Core, Network, Gui, Widgets, Xml, linked D-Bus and OpenSSL are built with
Qt 6.11's integrated WaylandClient, its private CMake target, the native
`qtwaylandscanner` and `qwayland` plugin. Offscreen and minimal QPA remain
available. Thirteen required feature checks reject silently missing features.

The configuration uses raster rendering, FreeType, HarfBuzz and POSIX
collation. OpenGL/GPU, XCB, fontconfig and ICU are disabled. The recipe
accepts native OHOS armv8 shared builds. Cross compilation and static builds
are excluded because code generators and runtime tests execute locally.
The consumer exercises interfaces used by layer-shell-qt; full KDE or
HarmonyOS desktop integration has not been validated.

## Reproduction

```sh
conan create archives/q/qtbase/6.11.1.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build='qtbase/*'
```

The default build runs seven cross-module targets and all 21 Wayland
targets. `-o 'qtbase/*:full_tests=True'` builds and attempts the complete
platform-selected CTest inventory; this validation option is excluded from
the package ID. Required command and assertion failures propagate nonzero
exits. `QTBASE_SOURCE_ARCHIVE` may supply the checksum-verified source.
`QTBASE_DATA_ARCHIVE_DIR` may supply the three checksum-verified official
data archives. Otherwise `source()` downloads their public URLs.

## Corrections and preserved behavior

| Area | Change and validation |
|---|---|
| Platform/ABI, 0001–0007 | Unix shared-library rules, existing cancellation capability, portable hashing and regular SONAME files. The ordinary shared-library consumer validates SONAME and runtime dependency paths. |
| D-Bus, 0009 | Use the error-reporting machine-ID API when linked D-Bus is at least 1.11.14; preserve the older/dynamic path. Missing machine-ID data no longer aborts the process. |
| File I/O, 0010–0011 | Clear transient stdio flags and stale errno before retry, check directory separators before creating a file, and use numeric UID if the passwd entry is absent. Native pipe/FIFO/socket tests and interrupted EOF consumer pass. |
| Test fixtures, 0012–0013, 0017–0020 | Use the configured moc compiler, provide HarmonyOS selector data, create owned temporary paths, restore the fatal-race handler explicitly, and skip five cancellation cases only when the existing capability is disabled. |
| Consumer metadata, 0014 and recipe | Export Wayland/XKB/scanner bridges, transitive headers/libraries, native build/run environments and the Core platform CMake directory. A fresh consumer uses ordinary CMakeDeps and CMakeToolchain without per-consumer dependency repairs. |
| Signals, 0016 | Restore the previous signal action before forwarding. The complete upstream QtTest self-test program passes and retains actual crash behavior. |
| Trash, 0021 | Use Qt's existing rename fallback when hard links return EACCES. Retain exclusive metadata creation, ownership checks and permission checks. A private-storage exact-content move passes; shared-volume ownership failures remain recorded. |
| Fonts, 0022 | Load font collections, recognize PANOSE monospacing, validate cmap coverage and choose an available fallback font. Native font, font database and raw-font programs pass. System fonts remain device assets. |
| POSIX IPC, 0023 | Hash the full original name to bounded SHA256 hex before deriving a distinct internal semaphore key. Preserve the public shared-memory key, locking and error propagation. The fresh consumer's 221-byte key and two child writers produce exactly 400. |
| IPC fixture, 0024 | Use the existing PID/sequence key generator and per-case cleanup. Preserve deprecated-constructor, create-failure and attach-success assertions. The complete program and its repeat pass. |
| GUI fixtures, 0025 | Create owned home/etc/passwd and directory fixtures; wait for the original positive row-count condition before inspecting the async model. Make child text wider than the minimum header width. Completer, both file-dialog programs and tree view pass. |

Existing Qt feature options select working POSIX IPC and named temporary
files: `FEATURE_ipc_posix=ON`, `FEATURE_sysv_shm=OFF`,
`FEATURE_sysv_sem=OFF`, `FEATURE_linkat=OFF`. Earlier patches 0008 and 0015
are superseded by these configuration options. There are 23 current patches.
The generic IPC naming change needs separate review for sandboxed Darwin
application-group names before reuse outside this OHOS-only package.

The locked Wayland cursor/scanner dependencies require private re-signing.
The scanner's stale absolute Expat NEEDED entry is relocated to its basename.
`runtime-provenance.json` records original, signed and packaged hashes.
Atomic replacement avoids overwriting mapped signed inodes.

XKB 2.41 and Adwaita 46.0 data are generated from checksum-pinned official
sources and include their licenses. All 59 cursor files are regular files.
Timezone files are generated from checksum-pinned IANA tzdata2025b and
tzcode2025b using the configured native C compiler. All 341 canonical zones
and 257 aliases are ordinary TZif files; data no longer depends on the
build worker's system timezone archive. Explicit `TZ`, including empty UTC,
is preserved.

## Collected native results, 2026-09-08

Environment: HarmonyOS PC / HongMeng Kernel 1.12.0, AArch64, Clang 15.0.4,
CMake 4.1.2 and OHOS Conan 2.29.1. Official framework: `090ac16c6073191805e144d97438bdbf976d7ce1`.

| Validation | Actual result |
|---|---|
| Final full76 | 532 executed: 526 passed, 6 failed, no timeout or skipped executable; build exit 0, CTest exit 8; serial, 900 seconds per program. |
| Official ConanVerifier | G0/G1/G2/G3/G4/L2/L4/L5 passed, including a clean-source build. |
| Official W3 | Fresh build, 7 base + 21 Wayland programs, packaging and ordinary consumer passed. |
| Fresh installed-package consumer100 | 44 mandatory checks + 2 font checks passed. |
| Copied native kit | 35 mandatory runtime + 2 font + 20 Wayland checks passed; actual Qt/dependency file origins verified in three executables. |
| Install/package readiness | Real qmake/qtpaths version checks and verified archive passed the unchanged official readiness check. |
| Local verification | 23 patches replayed; 19 recipe regressions and real CMake install-scope check passed. |

Full-suite archive SHA256: `834bb063e44b315167639e674a63c9e21056370d8ce6691bde13dc599afb9cb7`.
W3 log SHA256: `d866d93aa330d74a6076abe41888acf36a63e9b21a40e1de83a5a841aa04e756`.
Actual W3 reference: `qtbase/6.11.1.2#6987b9588536f153065fd7bbbe055d40:16b02108963dfa180909182973c9f449f0c4490e#377eefb9e2b783e8f4c1ddeff52e1fbc`.
Native kit SHA256: `33788add62fcf2034956865a71064671c8a6aa80215420f3ff8d4ad3e9f0560a`.

The 44 consumer checks are 9 CMake target checks, 18 offscreen, 11 system,
4 codegen/shared-library and 2 exact expected-error exits (97 and 65).
The copied binary invocation has 35 mandatory runtime checks because the
9 CMake checks belong to the recorded fresh compilation. Fonts add 2 and
Wayland adds 20. No tests from separate denominators are added together.

## Remaining failures and verification boundaries

The six full-suite failures are QFile (701/10/1 QtTest rows), QTemporaryFile
(60/1/0), QPluginLoader (89/1/0), QPlugin (11/1/0), QCollator (23/2/57),
and QLocalSocket (79/2/0). These are passed/failed/skipped rows within each
program, separate from the 532 programs. Raw failures remain unchanged.

Trash cases encounter shared-volume ownership, home and symlink conditions;
an independent private-storage exact-content trash operation passes. Plugin
cases modify signed ELF files. POSIX collation without ICU lacks the numeric
and punctuation options. Socket mode bits are correct while native access(X_OK)
returns EACCES. Detailed observations, probes and boundaries are in the
external full76-failure-analysis.md. These exceptions still need review.

The 532 entries are CMake-selected registrations; 710 source registration
sites and 846 source files are different inventories. Without a session bus,
the QtDBus suite is unregistered while the library remains enabled. QtTest
capability skips stay in the raw logs. Full-tests mode propagates CTest failure.

Before installation, the recipe uses Qt's QT_BUILD_TESTS_BY_DEFAULT=OFF to
exclude test data, including foreign-architecture ELF parsing fixtures, from
the package. It retains the full source/build and all product files. Native
ELF architecture/signature checks remain strict. Restore ON before manually
rebuilding all tests; full_tests=True configures this automatically.

The first official finish exit is 1; its raw receipt is retained.
The global knowledge check reports existing empty fields in E219/E253/E305.
Two automatically added resource mirror lists are the only source-metadata
differences. restore-meta98 verifies unchanged checksums/other fields,
restores the public URLs and verifies all 48 guarded inputs. Original
integrity-failure and W3 receipts remain unchanged.
The separate readiness112 check follows actual installed-tool/runtime/archive
verification. The legacy generic source-check warning is retained separately
from the passing Conan G0/G2 gates. No generated W3 receipt was edited.

Path C remains a candidate. PF1-PF8 pass; PF9 rejects software-level metadata
required by the repository structure, including commands.json. The framework
conflict and nonpassing preflight are retained. Public CI and post-commit W4
are participant publication steps. System desktop, GPU and complete KDE/
layer-shell deployment are outside the verified result. The participant
retains Git staging, commit, push, PR and task-portal operations.

## 最终状态

Native build and package verification are complete with status built. W3 and
the copied-kit consumer passed; the complete upstream run retains 526 passed
and six failed programs. The original finish exit 1 is preserved above.

The current independent source review passes with framework fix 09b080fd4;
its separate PR is !8966 and still awaits mainline merge. No framework change
is included in this package. The user has authorized source submission;
public CI, task-version mapping and C review remain pending.


## CI #42411 timezone source correction

CI #42411 passed the L0 dependency, commands.json, directory and branch gates.
Conan create then stopped in probes/prepare_timezone.py because the helper
required a system tzdata2025b archive. The error check covered the header,
format and version together; the worker's actual tzdata version was not
printed. This failure was unrelated to PF9.

The corrected recipe obtains both tzdata2025b and tzcode2025b from IANA with
fixed SHA256 values and builds the upstream zic compiler using the configured
native C compiler. It no longer reads /system/etc/zoneinfo/tzdata. The helper
generates every default IANA zone, then materializes Link aliases as identical
regular files for the OHOS filesystem. Explicit application TZ behavior and
the package's TZDIR environment are unchanged.

Validation on the corrected helper:

- 598 generated TZif files: 341 canonical zones and 257 aliases. Every file
  matches independently built, unmodified upstream zic fed all original inputs.
- All 598 files parse with Python ZoneInfo; six known winter/summer offsets pass.
- Release mismatch, alias cycle, dangling alias and path traversal fail while
  preserving the previous output. Repeated generation removes stale entries.
- OHOS Clang 15 generation passes. All 598 target hashes match host reference.
- Existing native Qt consumer with the new TZDIR passes 11 system assertions.
- Complete native tst_qtimezone and tst_qdatetime both pass under the same
  TZ setting used by the recipe. An earlier ad-hoc run omitted that TZ setting
  and retained its systemZone failure; the recipe already supplies the setting.
- Actual Conan source() checks pass with all four pinned auxiliary archives;
  existing 19 recipe regression tests pass.

The earlier full76 526/532 result, W3 receipt and binary archive remain evidence
for their original recipe/runtime-data snapshot. This change does not modify
patched Qt C++ sources. A new CI run will establish the final whole-recipe
build/package result; no old receipt has been overwritten or marked as a new run.

## CI #42456 and #42465 source download correction

Both attempts failed during Qt source download, before the corrected timezone
builder ran. The canonical Qt endpoint redirected to ftp.jaist.ac.jp, which
returned incomplete data or timed out. The recipe now uses Qt's listed
qt.mirror.constant.com mirror first and retains download.qt.io as fallback.
Both URLs are published in the canonical file's .mirrorlist. A complete
50,648,500-byte download has the unchanged upstream SHA256
d9594a31228aa23ad6b531719a29b45f0f3989fe6c136d45767ea179f233c1ac.
Conan's normal multi-URL downloader and hash verification remain in use.
No source, patch, test assertion or runtime behavior changes in this repair.

## CI #42478 optional system-package probe correction

The official source mirror and fixed IANA timezone generation passed on CI.
CMake then loaded a stale system freetype-config.cmake referencing a missing
libfreetype.a even though FEATURE_system_freetype was already OFF. Qt probes
these optional system packages before evaluating the feature selection.

The recipe now sets CMake's CMAKE_DISABLE_FIND_PACKAGE flags for the six
WrapSystem packages already selected from Qt's bundled sources: ZLIB, PCRE2,
Freetype, Harfbuzz, PNG and Jpeg. It does not alter Qt sources or disable the
bundled library targets, the main features or required external dependencies.

An isolated broken Freetype configuration reproduces the failure with the
original settings. The corrected settings pass with the unchanged upstream
Qt finders; a missing unrelated REQUIRED dependency still fails. Fresh native
Conan generate and full Qt configure reproduce the original failure and pass
with the fix. CMakeCache records all six QT_USE_BUNDLED choices ON, all six
system features OFF, and the font/image features remain ON. All 19 existing
recipe regressions pass. Logs are retained outside the source PR; the new
whole-recipe CI result remains pending.

## CI #42503 upstream Wayland runtime directory correction

The complete product and selected test targets compiled. All seven base
programs passed, but 20 of 21 Wayland programs failed. Nineteen failures
explicitly print bind() Operation not permitted; the reconnect fixture also
fails to create its display. The sole passing program tests connection failure.
The final failure is in upstream execution, despite the bot's network category.

CI sets TMPDIR under the shared Documents filesystem. Native probes reproduce
AF_UNIX bind errno 1 there; chmod 0700 also leaves mode 02771 and a synthetic
owner. The application's /data/storage/el2/base/cache supports owned 0700
directories and an actual bind/listen/connect/accept/data exchange. The same
unmodified Wayland group fails with the shared temporary parent and passes
all 21 programs with the private parent.

The recipe creates an independent temporary directory per group, checks its
ownership/mode and probes an AF_UNIX connection below a simulated Qt temporary
subdirectory. On OHOS it tries the application cache after an unusable default
parent. Both TMPDIR and XDG_RUNTIME_DIR are scoped to that group: upstream
mock compositors create QTemporaryDir and overwrite XDG_RUNTIME_DIR themselves.
All rejected candidates are recorded; no usable candidate is a fatal result.
No upstream source, assertion, target selection or CTest timeout changes.

The actual candidate recipe group method, with a shared TMPDIR inherited at
process start, passed 7 base and 21 Wayland programs on the target. Both groups
selected the private cache, restored the original environment and removed
their own directories. Twenty host recipe checks pass; the mocked CTest
failure-propagation check also verifies environment restoration and cleanup.
Real socket behavior is established by the separate target runs. A new remote
whole-recipe CI result remains pending; CI #42503 and earlier receipts are kept.
