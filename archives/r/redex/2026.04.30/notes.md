# Redex 2026.04.30 adaptation notes

## Current state

- 2026-10-09: independent `apk-consumer-r003` completed one real installed
  `redex.py` APK conversion, RC0/no timeout, with the original frozen validator
  and release/postrelease 2/2. Conservative keep-all rules, exact runtime
  dependency libdirs, ZIP/DEX integrity, 21-pass statistics and before/after
  input/product hashes are bound in its own archive. This closes the disclosed
  APK-flow gap, not Android signing/alignment/install or semantic-equivalence
  coverage. Earlier APK r001/r002 FAILs remain unchanged. No native upstream
  test was replayed. See `reports/test-report.md` for precise scope and hashes.
- 2026-10-08: native r376 completed all 174 GoogleTest wrappers, 2009 leaves,
  the upstream Shell test and Conan consumer, with original-controller
  release/postrelease 2/2. Independent official-finish-r001 completed official
  W3 local CI, Conan consumer and Harmony-specific test 1/1. Its aggregate
  finish remains RC1 (`step5b,step8`), not overall PASS. The original result was
  archived after a subsequent reboot and its exact remote root was cleaned;
  neither consumed transaction is replayed. See `reports/test-report.md` for
  run IDs, tested trees, archive hashes and remaining submission work.
- The current declared patch set contains 18 files (`0001` through `0018`),
  unchanged during this post-W3 metadata update. Historical numbering and
  earlier failure descriptions below describe their original snapshots.
- W0 dependency recipe and OHOS/arm64 binary resolution passed with
  `--build=never` for Boost 1.91.0.1.1, JsonCpp 1.9.8, and
  zlib-ng-compat 2.3.3. The r376/APK-r003 exact published revisions are
  listed below. Official-finish-r001 has its own resolution/logs (including a
  different JsonCpp RREV), not the same dependency closure:
  - Boost: RREV `a87a5f6c933b59858076703e53cff426`, PID
    `01d92cf349a0dd98ff915f4bd99a04430171517f`, PREV
    `d3b8de724932d37020b2ebb660280e98`;
  - JsonCpp: RREV `92bd5a7a9ed9d84d9dc1d4bf643dbd39`, PID
    `01d92cf349a0dd98ff915f4bd99a04430171517f`, PREV
    `968821bc3df5aca7b074c18256cdf422`;
  - zlib-ng-compat: RREV `3d931a5aa0e9c95291b687d6555eea4b`, PID
    `6b129b068851896169fae42d399fa922d239ce8a`, PREV
    `c8a946e95258944780aa65d79e7ab164`.
- A generated CMake consumer resolves `Boost::filesystem`, `Boost::graph`,
  `Boost::iostreams`, `Boost::program_options`, `Boost::regex`, and
  `Boost::thread`; the Graph contract propagates `Boost::random` and
  `Boost::serialization`, and the installed package contains
  `boost/pending/disjoint_sets.hpp`.
- Product source is the official `v2026.04.30` archive with the verified
  SHA-256 digest recorded in `conandata.yml`.
- The official release gates were refreshed on 2026-08-08: Redex's newest
  upstream tag remains `v2026.04.30` at
  `cd1ada7cf735e4a4b85f1b88172421e264839e89`, and GoogleTest's latest stable,
  non-prerelease release remains `v1.17.0`.
- A fresh isolated official-remote OHOS/arm64 graph and install on 2026-08-10
  resolved `gtest/1.17.0` with RREV
  `ab1bc3bf51522490eef07a83c2dbd203`, PID
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5`, and PREV
  `489a70cbb1156b4d5594f8ce638b9630`. Both used `--build=never`; every node had
  empty `info_invalid`, no package was missing, and the binary was downloaded
  from `ohpcd`.
- The fresh Boost readback is bound to PR #5779 release builder 2 / #3211 /
  buildid 31048 at merge revision
  `716dbffc1d2c21736bfe299d391a3cbbe66332ca`. The downloaded package contains
  `boost/multiprecision/cpp_int.hpp` and exports `Boost::multiprecision`.
- The historical seventeen-patch candidate used strict `patch_ng` patches. The
  complete postimage has no `boost/format.hpp` references in the touched
  source targets, and `SplitHugeSwitchPass.cpp` uses the classic iterator
  `std::any_of` overload instead of the unavailable target-libc++ ranges
  overload. The ninth patch keeps the installed Python driver usable when the
  target runtime does not provide the `packaging` module. The tenth preserves
  the selected C++ standard during the Autoconf GoogleTest header probe. The
  eleventh stores `getopt_long()` in `int`, preserving its `-1` sentinel under
  target Clang's `-Werror`. The twelfth makes the Autotools bundling target use
  the Bash executable detected by `configure`, avoiding the upstream
  `#!/bin/bash` interpreter path on targets without `/bin/bash`. The thirteenth
  adds an explicit Autotools mode for frozen sample APKs: it requires both
  fixture SHA-256 values and rechecks each copied APK on every `all-local` and
  `check-local` entry, while leaving every test consumer and denominator
  enabled. This avoids trying to execute the Linux-host Android SDK `aapt2`
  binary on OHOS arm64. The fourteenth patch preserves all nine
  `ConfigFilesTest` leaves while making their dead-class-list fixture helper
  prefer the task-local `TMPDIR`; an unset or empty variable retains the
  upstream `/tmp` fallback for ordinary hosts. The fifteenth patch reserves
  the exact argument count in `FbjniMarker` before storing `string_view`
  descriptors. This prevents a vector growth from invalidating views into a
  libc++ short-string buffer while preserving the parsed method signature.
  The sixteenth patch classifies boxed Boolean fields and methods from their
  exact current-context descriptors rather than cached `Dex*` pointer
  identity. This preserves the `Boolean.TRUE`/`Boolean.FALSE` distinction
  across repeated `RedexContext` lifetimes and explicitly dereferences the
  singleton-object optional before classification.
  The seventeenth patch classifies the instruction's raw boxed-Boolean field
  before resolution, prefers a current concrete definition, and rejects any
  raw/resolved TRUE/FALSE mismatch. It also fixes the Boolean fixture's type
  descriptors, sorts resource IDs before graph-diff emission, and formats
  encoded bytes through `unsigned char`, removing target STL iteration-order
  and plain-`char` signedness from the test contract.
  The prebuilt-APK branch additionally passes 1/1 positive and 3/3
  fail-closed cases with zero `aapt2` invocations.
- Current acceptance is based on the separately identified immutable r376 and
  official-finish-r001 evidence, not this prose. No platform CI, publication or
  submission PASS is claimed. Patch 0018 uses complete boxed Boolean field
  descriptors for `booleanValue` folding; r372's earlier `boxed_boolean`
  failure remains recorded, and later passing runs do not by themselves prove
  the precise cause of that intermittent historical failure.

## Formal GoogleTest provider boundary

The r5 runner requires the official `gtest/1.17.0` package before any build or
test work. A failed initial graph is terminal; local source compilation and
closing-probe promotion are disabled. The closing probe must independently
resolve a real RREV, OHOS/arm64 package ID, and PREV with empty
`info_invalid`, otherwise the run cannot produce `W3_RESULT=PASS`.

The first target build reached CMake configuration and failed because upstream
requested `JsonCpp 0.10.5` in Config mode while Conan supplied the exact pinned
`jsoncpp/1.9.8` config. CMake's generated version check rejects that cross-major
request before loading the imported target. The portability patch therefore
lets Conan's exact recipe requirement own version selection and requires the
`JsonCpp::JsonCpp` target without repeating the obsolete upstream version.
A focused CMake probe reproduces the versioned failure and verifies that the
unversioned Config lookup succeeds with the required imported target.

The next target build completed CMake generation but failed at the first
`redex` source because `json/value.h` was not on that static target's compile
include path. Linking `JsonCpp::JsonCpp` only to the later `redex-all`
executable cannot affect compilation of the archive. The patch now links the
imported target publicly to `redex`, which propagates JsonCpp's include and
link usage requirements at the target where they are consumed.

A later exact target build reached `libredex/Debug.cpp` and showed that the
selective Boost package does not install `boost/stacktrace.hpp`. Redex includes
that header unconditionally, but uses `boost::stacktrace` only in its
`IS_WINDOWS` implementation; non-Windows targets use `execinfo` instead. The
third portability patch therefore guards only the Stacktrace include with
`IS_WINDOWS`, preserving the Windows implementation without expanding the
OHOS dependency closure for an unused header.

After Boost 1.91.0.1.1 was published, the fresh r108 target build passed the
Multiprecision dependency boundary and reached `libredex/PluginRegistry.cpp`.
`PluginRegistry.h` directly instantiates `std::string` in vectors, hashes, and
function signatures but included only `<functional>` and `<vector>`. The OHOS
libc++ headers expose only the `iosfwd` declaration on that path, so the build
failed with `implicit instantiation of undefined template
'std::basic_string<char>'`. The fourth portability patch adds the required
`<string>` include; it does not change runtime behavior.

The fresh r112 build passed `PluginRegistry.cpp` and reached `Show.cpp`, where
the selective Boost package does not install
`boost/locale/encoding_utf.hpp`. Unlike Stacktrace, this API is active on OHOS:
Redex uses `boost::locale::conv::utf_to_utf` only to append one already parsed
Unicode code point. The fifth portability patch replaces that single operation
with the standard UTF-8 byte encoding while retaining Redex's existing MUTF-8
surrogate-pair assembly and control-character escaping. Upstream
`DexAnnotationTest.EscapeStrings` covers both a supplementary-plane code point
and an overlong MUTF-8 NUL.

The later r116 build applied the complete Boost.Format removal, passed the
earlier dependency and source boundaries, and reached 66% before
`SplitHugeSwitchPass.cpp` failed with `no member named 'any_of' in namespace
'std::ranges'`. The file already included `<algorithm>`; the target libc++ lacks
that ranges algorithm while the classic iterator overload is available. Patch
0008 binds `all_interactions()` once and uses
`std::any_of(begin, end, predicate)`, preserving short-circuit behavior without
changing the dependency closure.

## Build boundary

The upstream CMake project builds and installs `redex-all`, `redex.py`, the
`pyredex` modules, generated API-level data, headers, and internal static
libraries. It does not register the complete upstream test suite.

Redex is an application recipe with one supported dependency closure. The
official Boost and JsonCpp RREVs publish the shared OHOS/arm64 packages used by
the executable; their static package IDs do not resolve from the official
remote. The recipe therefore does not expose a misleading `shared=False`
application option. Artifact validation covers the executable's shared
dependency contract and the three upstream internal static archives.

The complete upstream denominator must come from the configured Autotools
runner plus `--gtest_list_tests` for every GoogleTest executable. Wrapper and
source-file counts are discovery evidence only.

## Runtime boundary

The final target validation must cover both the native `redex-all` executable
and a real APK transformation through the same-package `redex.py` driver.
Simple help or version output is not sufficient for final acceptance.

Current evidence qualification: r376's state receipt proves `--show-passes`
and Python-driver `--help`, not an end-to-end `redex.py` APK transformation.
The old APK-flow requirement above is retained as a disclosed coverage gap;
neither r376's test counts nor r001's Harmony test can substitute for it.

## Historical validation and successor boundary

- The historical r81 candidate used a create-new transfer-only transaction.
  Its test counts are prior evidence and cannot validate the current dependency
  update.
- The current W0 resolves Boost 1.91.0.1.1, JsonCpp 1.9.8,
  zlib-ng-compat 2.3.3 and
  GoogleTest 1.17.0 from `ohpcd` with OHOS/arm64 and `--build=never`; exact
  RREV/PID/PREV values are recorded above.
- r93 is preserved as an immutable consumed launch. It failed during
  `conan create` with
  `fatal error: 'boost/multiprecision/cpp_int.hpp' file not found`, then
  completed exact remote cleanup. It must never be relaunched or relabeled.
- r108 is preserved as an immutable consumed launch. It passed the published
  Boost Multiprecision boundary, then failed during `conan create` because
  `PluginRegistry.h` used `std::string` without including `<string>`. Its exact
  task root was cleaned after a zero-process readback and two absent scans.
- r110 is preserved as an immutable consumed launch. Its frozen 0004 patch
  used a zero-context hunk whose line header was offset by one; Git accepted
  the offset locally, but Conan `patch_ng` correctly rejected it before
  compilation. The successor patch uses the exact official-source line and
  explicit delete/add records for adjacent blank lines so both the repository
  whitespace gate and strict `patch_ng` parsing retain full anchoring. The
  r110 task root was cleaned after a zero-process readback and two absent
  scans.
- r111 is preserved as an immutable consumed launch. The corrected 0004 patch
  applied through Conan `patch_ng`, and target compilation passed
  `PluginRegistry.cpp` before reaching 26%. The host controller process then
  disappeared without a local RC/meta record; the remote failure envelope
  recorded `conan-create` RC 120 with no compiler diagnostic. This is a
  transport/controller-lifetime failure, not a source failure. The r111 task
  root was cleaned only after the remote run had published
  `W3_RESULT=FAILED`, all owned locks were absent, the root process count was
  zero, and two absent scans passed.
- r112 is preserved as an immutable consumed launch. Its detached host
  controller remained alive and proved the controller-lifetime repair, the
  exact patch-ng 0004 applied, and target compilation passed
  `PluginRegistry.cpp`. The build then failed at 30% because `Show.cpp`
  actively included the unselected Boost.Locale header. The r112 task root
  was removed only after `W3_RESULT=FAILED`, `conan-create` RC 1, zero owned
  processes/locks, and two independent post-clean absent scans.
- r116 is preserved as an immutable consumed launch. The complete Boost.Format
  removal compiled, and the target build reached 66% before the missing
  `std::ranges::any_of` library capability stopped compilation. The failure log
  and 63-file result archive were read back exactly, and the unique remote root
  was removed only after two independent absent scans.
- r118 is preserved as an immutable prelaunch controller attempt. Its
  knowledge-complete tree passed local gates, independent W4, strict readiness,
  and production `ValidateOnly`, but endpoint `10.62.148.108:2222` timed out in
  `00-transfer-layout`. No `LAUNCH-ATTEMPT.json` was created, so its launch count
  remains 0/1; the controller is not retried and device continuation requires a
  fresh successor run and task root.
- r198 is preserved as an immutable consumed launch. The HMDFS configure repair
  passed, then target Clang stopped `tools/redexdump/RedexDump.cpp` because a
  `char` result from `getopt_long()` cannot represent the `-1` sentinel on that
  target and the resulting comparison is a `-Werror` diagnostic. Its failure
  archive was read back exactly, the unique remote root was removed, owned
  process count reached zero, and `POSTRELEASE_PASS` was committed. r198 must
  never be relaunched or relabeled.
- r202 is preserved as an immutable consumed launch. It passed configure, the
  task-local Bash boundary, the header-only Boost.Regex probe, and the Python
  bundler, then failed while `make -j1 check TESTS=` recursively built the
  upstream sample fixtures. The Android SDK 29.0.2 Linux-host `aapt2` returned
  `Exec format error` on OHOS arm64 before the upstream GoogleTest phase. Its
  result archive was read back exactly, the transaction committed 12/12 WAL
  phases, the unique remote root was removed with zero owned processes, and
  postrelease passed. r202 must never be relaunched or relabeled.
- r203 is preserved as an immutable consumed launch. It passed the prebuilt-APK
  boundary and then failed before the Java fixture build because the target
  input did not provide `javac`. Its exact remote root was removed with zero
  owned processes and postrelease passed. r203 must never be relaunched or
  relabeled.
- r205 is preserved as an immutable consumed launch. The task-private JDK and
  the memory-gated build parallelism passed, and the full upstream GoogleTest
  phase started with `BUILD_JOBS=2` after the target reported
  `MemAvailable=5122048 kB`. `ConfigFilesTest.dead_class_list_standard_format`
  then failed because its helper hard-coded read-only `/tmp` instead of using
  the already exported task-local `TMPDIR`. The failure archive was read back
  exactly, the remote root was removed with zero owned processes, and
  postrelease passed. r205 must never be relaunched or relabeled.
- r208 is preserved as an immutable consumed launch. Patch 0014 passed all
  9/9 `ConfigFilesTest` leaves on the target, proving the task-local `TMPDIR`
  repair. The later `FbjniMarkerTest.ProcessFunctionTest` failed while resolving
  `m2(Object, byte)`: the argument descriptor stored `string_view` values into
  a backing `vector<string>` before that vector finished growing. The first
  descriptor fits libc++ short-string storage, so the next vector growth moved
  its inline bytes and left the view stale; common host libstdc++ stores that
  descriptor on the heap and therefore masked the defect. r208 completed an
  exact failure-archive readback, removed its remote root with zero owned
  processes, and passed postrelease. It must never be relaunched or relabeled.
- r212 is preserved as an immutable consumed launch. The first host controller
  lost one terminal probe with SSH RC 255, after which the frozen recovery
  controller rebound the same boot ID, UID, runner PID/start token, and
  `launch_count=1`. The runner completed 77 unit GoogleTest wrappers before
  `method_inline_test` reported the single failing leaf
  `MethodInlineTest.boxed_boolean`: target constant propagation removed all
  five `Boolean.FALSE` calls instead of retaining them and removing only the
  `Boolean.TRUE` call. The fail-fast runner did not execute the remaining 72
  unit wrappers, 25 integration wrappers, or the shell test. Its exact
  incomplete archive was read back before cleanup; all 12 WAL phases were
  committed, the task root reached zero owned processes and was removed, and
  postrelease passed. r212 must never be relaunched or relabeled.
- r216 is preserved as an immutable consumed launch. It completed all 174/174
  GoogleTest wrappers and the one shell test; 170 wrappers passed and four
  wrappers failed. The failures isolated boxed-Boolean current-context
  identity, unordered resource graph-diff emission, and signed-`char` hex
  formatting. Its exact result archive was read back, all 12 WAL phases were
  committed, the task root reached zero owned processes and was removed, and
  postrelease passed. r216 must never be relaunched or relabeled.
- A current-tree acceptance record is valid only when it executes all 174
  default GoogleTest wrappers (2009 enumerated leaves), the upstream shell test, the real `redex.py`
  APK transformation, and the Conan consumer test against Boost 1.91.0.1.1.
- r80 is preserved as an immutable consumed launch boundary: it reached the
  unique launch phase without a durable terminal log, so it was not retried.
  r81 is the only successor transaction and uses a new remote sibling root.

## 关闭本轮原生构建验证（提审未完成）

Native r376 is PASS/released. Official r001's W3 substep and Harmony consumer
are PASS, while its aggregate finish remains FAIL/RC1. APK consumer r003 is
independently PASS/released and closes the historical conversion coverage gap
for the bound strings fixture and conservative keep-all rules. Reports preserve
each run, tested tree, dependency resolution and scope separately. The
software remains `built`, not published or submitted. No hand-written CI
result, retired packaging artifact or staging marker is used to claim closure.
