# itk 5.4.6

- Claimed OHPCD task 192 as `2301_80739235` on 2026-08-08T17:43:24Z.
- Official upstream stable release: ITK v5.4.6. The newer v6.0b02 tag is a
  prerelease and is excluded from the stable-version gate.
- Source archive: official GitHub release asset
  `InsightToolkit-5.4.6.tar.gz`, SHA256
  `1177567965a2522c53f7c77ed222afd619262f508caaf026646b21e275971e95`.
- Dependency gate: `ITK_USE_SYSTEM_LIBRARIES=OFF` keeps ITK's bundled
  third-party code in-tree; the Conan graph has no third-party Conan
  requirements.
- Fresh graph-only W0 for current main `807fa2c350480cb15271d1891f23b2b991916fd5`
  passed with the OHOS armv8 profile in isolated Conan home
  `E:\HarmonyPC\conan-homes\slot4-itk-5.4.6-w0-20260810T111921Z-807fa2c3`:
  root `itk/5.4.6`, graph node count 1, dependency count 0,
  `info_invalid` empty, missing/invalid binary nodes 0. Evidence:
  `E:\HarmonyPC\source-audit\itk-5.4.6-slot4\w0-20260810T111921Z-main-807fa2c3\w0-meta.json`.
- Build scope: the package enables `ITKCommon` and, whenever Conan proves the
  target binaries can run, enables `BUILD_TESTING` plus `ITKGoogleTest` and
  executes the complete generated CTest inventory. It disables default
  optional module groups, examples, Python wrapping, and GPU support. This
  avoids unpublished dependency chains and GPU/hardware paths without
  suppressing the selected module's upstream tests.
- ITK rejects long build directory paths during CMake configure, so the recipe
  uses `cmake_layout(..., build_folder="b")`. W3 must use a short isolated
  Conan home.
- Authorized-device W3 R2 local-sourcefix attempt
  `20260811T100118Z-task192-807fa2c3-215229-local-sourcefix-r2` reached Conan
  configure and failed with RC 49 because upstream NIFTI set
  `NIFTI_SYSTEM_MATH_LIB` to `NOTFOUND` after `find_library(... m)` could not
  find a separate `libm` on OHOS, even though CMake had already found `floor`,
  `pow`, and `sqrt`. Full root evidence is preserved at
  `E:\HarmonyPC\source-audit\itk-5.4.6-slot4\device-w3-prep-20260811T082404Z-main-807fa2c3-local-sourcefix\w3-r2-20260811T100118Z-215229\20260811T100118Z-task192-807fa2c3-215229-local-sourcefix-r2-full-evidence.tar`,
  SHA256
  `bb7def1e97c820a4becffd0e73cb589e13eae7bc5416a0b040adfb8eba94bff2`.
  The recipe now pre-seeds `NIFTI_SYSTEM_MATH_LIB` to the empty string for OHOS
  targets so NIFTI does not require a nonexistent separate math library.
- Authorized-device W3 r3c used the exact frozen tree
  `dd5f7d11846ea05b8219c76e378031bdc8e8e054` once and reached 1% of the
  single-job build. NIFTI configured successfully, then KWSys selected
  `ProcessWin32.c` because CMake did not set `UNIX` for the unknown
  `HarmonyOS` system name. Compilation failed on the unavailable `windows.h`.
  The preserved terminal readback reports target RC 49 and Conan log SHA256
  `06ae25a23a6577e4f3a2f315055e89e0ffae676724db2526acde5ea54eb41db3`.
  The new portability patch reserves `ProcessWin32.c` for `WIN32`, probes
  `<unistd.h>` plus linkable `fork` for otherwise unknown systems, selects
  `ProcessUNIX.c` only when that concrete POSIX process capability exists,
  and fails configuration when neither implementation is justified. It adds
  no platform-named source conditional.
- Authorized-device W3 r5 used the exact staged tree
  `2d28b75c2021a5a3202b827eca1253edfc7ec656` once. The NIFTI and KWSys
  repairs passed, and the single-job build reached 98%, where vendored TIFF
  selected `tif_win32.c` through `if(NOT UNIX)` and failed on `windows.h`.
  The r5 terminal reports target RC 49 and Conan log SHA256
  `653e1e95942efa8b09ddbb460aa0d6f6718e0f8abb30a88a1834057748cf887a`;
  release and two post-release clean scans passed. The TIFF portability patch
  now reserves `tif_win32.c` for CMake's positive `WIN32` predicate. Other
  systems select `tif_unix.c` only when `UNIX` or a compile-and-link probe for
  the file-descriptor APIs used by that source succeeds, and configuration
  fails when neither implementation is justified. It adds no platform-named
  source conditional.
- Authorized-device W3 r13 used the exact staged tree
  `7d1af51935ee87b1dbfdb9f3465825bfb5161e88` once. NIFTI configured,
  KWSys compiled `ProcessUNIX.c`, and TIFF compiled `tif_unix.c`; the build
  reached the final `itkTestDriver` link. Vendored libpng headers enabled ARM
  NEON from target compiler capabilities, but its CMake source list omitted
  `arm_init.c`, `filter_neon_intrinsics.c`, and
  `palette_neon_intrinsics.c` because the cross build's
  `CMAKE_SYSTEM_PROCESSOR` did not match the upstream ARM string test. The
  resulting archive referenced four `itk_png_*_neon` functions without their
  implementations. Terminal target RC was 49, Conan log SHA256 was
  `4deda945c57c1bacc68ebcf3f180718c3372fb8280c1cc73018661209281fde7`,
  and release plus two clean scans passed. The PNG portability patch preserves
  upstream ARM and Apple selection and adds a compiler-capability fallback
  that appends the three NEON implementation files only when a target C probe
  can include `arm_neon.h` and compile a NEON intrinsic. It adds no
  platform-named conditional.
- Authorized-device W3 r15 used exact staged tree
  `ad7ea2dd04fa18e851825fee2c7189d8bddd7a09` and controller
  `726b8192fee2a2da2a05dc9f8a1cd4da88357c4d8a4977978ec06a59f3dba6b5`
  once on `10.62.215.229:2222`. NIFTI configuration, KWSys POSIX process
  selection, TIFF POSIX I/O selection, and the PNG NEON capability fallback
  all passed. The complete target returned RC 0 with Conan log SHA256
  `f75a7af89ef41d50c382d552c99e49d59f1edafda08d00102f32e02c63f37965`.
  Terminal/release summary SHA256
  `8f7d3167058fa64569425c98188d9612264737c0dcc6e4ea1c7b9a79344e7936`
  records launch count 1, terminal PASS, release PASS, and two clean
  post-release scans. The exact-owner scheduler release also returned RC 0.
- Self-allocated authorized-device W3 r16 used exact staged tree
  `a61f057bf42bbdf6caf4841d1da33b02b7b847fe` once. The NIFTI, KWSys, TIFF,
  and PNG repairs remained effective, but enabling the complete upstream test
  graph activated KWStyle's `ExternalProject` Git clone at build 0%. The
  network-restricted target returned RC 49; Conan log SHA256 is
  `2d288fff1003c94e1af687d3ee3f0480cc220af5d1e75a6386705c6b19c4e867`.
  Terminal SHA256
  `50cbe159bfbec24db0484c92b5febdf25a5bf25a8a333534cb9e11027682d90e`
  records launch count 1, release PASS, and two clean post-release scans. The
  recipe now freezes KWStyle commit
  `6971e89ec4c763601edf1d0ea0d6f71d42fbca5d`, verifies archive SHA256
  `c8614034e6a7a5b952c6bab956cc668288fbdf4543d5473305e8fdc939979927`,
  and binds its extracted directory with an empty ExternalProject download
  command. r16 is immutable and must not be retried.
- Self-allocated authorized-device W3 r25 used its exact frozen successor once.
  The local KWStyle archive path and the complete upstream test graph remained
  effective, but KWStyle's bundled Boost selected its POSIX sleep branch from
  `BOOST_HAS_PTHREADS` and then called the optional
  `pthread_setcancelstate` API, which the target pthread headers do not
  declare. The target returned RC 49; Conan log SHA256 is
  `76d2e05f9c69468c682e2c4d02a48b0551955c37187fe123f7744d033e467a33`,
  and terminal summary SHA256 is
  `6fd130015f1b980fc91d4dc38fa45a14208a35008f7337b2e3c01265d2b571b2`.
  Release and two clean scans passed. The new KWStyle patch links the symbol
  probe through `Threads::Threads`; when `pthread_setcancelstate` is absent,
  it defines Boost's task-local cancellation-state guard while preserving the
  POSIX `nanosleep` path. The fix uses no platform-name conditional. r25 is
  immutable and must not be retried.
- Self-allocated authorized-device W3 r26 used exact staged tree
  `dfcbabe9a67f42a3fefac4b45ca4dab209ecd06e` once. The local KWStyle source
  and pthread cancellation capability repair passed: the symbol probe reported
  `pthread_setcancelstate` unavailable and `KWStyleLib` built through 68%.
  KWStyle then built its own bundled KWSys copy, whose independent
  `if(NOT UNIX)` selector still chose `ProcessWin32.c` and failed at 70% on
  missing `windows.h`. Target RC was 49 and Conan log SHA256 was
  `5997d90c89740f17000d7c3edd52cebbc4e67dbde3785b3e271cec766db107ec`.
  Terminal/release summary SHA256 was
  `05270987021d9350a69245162164ea8f84e232b811aa5202cfa386d7b64b9049`;
  release and two clean scans passed. Patch6 applies the already validated
  positive `WIN32` plus linkable POSIX process capability selector to this
  separate KWStyle KWSys source copy. r26 is immutable and must not be retried.
- Self-allocated authorized-device W3 r29 used exact staged tree
  `cc39d7b0bfce1dd97a3c21e3d722b0c4d955c39c` once. The package built and
  installed, its consumer passed, and target CTest executed 617/617 with zero
  failures. The strict 618-test verifier correctly rejected the run because
  `itkImageFillBufferTest4.1` alone was absent. CMake repeatedly reported
  `Problem parsing /proc/meminfo`, leaving `ITK_COMPUTER_MEMORY_SIZE` below the
  test's `GREATER 4` gate even though sealed preflight measured 32680776 KiB
  total and 18911232 KiB available memory. Conan log SHA256 is
  `3b4720936524ddd90ffbd34d2f8ed6367bd7078e8699b984a5126c559745cec2`;
  terminal summary SHA256 is
  `f49b29a08bd00e2ba19b2e5892fd0814f943920473c7294754f9fee99510a3d2`.
  Release and two clean scans passed. The successor requires a validated
  `ITK_COMPUTER_MEMORY_SIZE` before runnable OHOS tests configure; its target
  runner derives the value from `MemTotal` and preserves ITK's 80% budget.
  r29 is immutable and must not be retried.
- Self-allocated r30 never reached the device. Its outer wrapper claimed the
  free endpoint with predecessor tree
  `cc39d7b0bfce1dd97a3c21e3d722b0c4d955c39c`, while the final freeze and
  live candidate tree were
  `b430046f8eddc714a40495e8faa17b8bfae051c0`. The controller failed its
  local `HEAD/tree drift` gate before evidence creation, SSH, transfer or
  launch, and the wrapper released the exact owner record with RC 0. The
  successor binds live Git, authority, controller and wrapper allocation trees
  byte-for-byte and exercises that projection in the complete offline
  transaction matrix. r30 is immutable and must not be retried.
- Self-allocated r31 reached the target runner once but stopped before Conan.
  Both manifest validations passed; the memory helper then evaluated
  `32680776 * 80` in the target shell's 32-bit integer arithmetic and
  overflowed to a `-16` GiB budget. Target RC was 48, Conan log was absent,
  terminal summary SHA256 was
  `2f36ed6d80b95cad3a3997ad0016115021bd348ce3fda97e92f9e0b655583426`,
  and release plus two clean scans passed. The successor divides KiB to MiB
  before applying the 80% factor and caps the supported budget so every
  intermediate remains within signed 32-bit range. r31 is immutable and must
  not be retried.
- Self-allocated authorized-device W3 r32 used exact HEAD/tree
  `790889af641422d7f71c49947d1cfe15f1776dae` /
  `c89da60d64341a57de77c5548a1a1ae1e7dd08b0` once. The target build and
  install passed, CTest executed 618/618 with zero failures including
  `itkImageFillBufferTest4.1`, and the installed-package consumer returned
  RC0. Conan log SHA256 was
  `238574049d23a420d6856073da965e3f2906d3cba59f3cb1f0dbee786269c7ef`;
  terminal/release summary SHA256 was
  `e20cd358d3ef3a3b5e62ceb1834d26911bebdf910976ed2e81f52faf3a3850d0`.
  Release and two clean scans passed.
- Exact-current-HEAD CI build `#26077` (global buildid `28791`) proved that
  draft placement now passes G0, then failed before configure because the
  runnable OHOS `conan create` environment did not provide the task-controller
  variable `ITK_COMPUTER_MEMORY_SIZE`. The recipe now retains a validated
  explicit override but, only for runnable OHOS without one, parses exactly
  one local `/proc/meminfo` `MemTotal: <integer> kB` field and derives the same
  bounded 80% GiB budget. The create-new local matrix passed 30/30; replacement
  CI and a new exact-snapshot W3 remain required because the recipe changed.
- Exact-current-HEAD CI build `#26137` (global buildid `28851`) passed G0 and
  built KWStyle, then failed while generating an ITKData baseline because the
  clean Conan export did not contain CID object
  `bafkreia46j4a53hnz6iup2x6x5fjrudaseyrte3y4fce5s3yytk53fd6aa` and URL
  fallback was correctly disabled. The recipe now exports a manifest-bound
  14-object store, defaults runnable builds to
  `self.source_folder/test-data/Objects`, preserves validated explicit
  overrides, leaves non-runnable cross builds unbound, rejects links and every
  missing/extra/duplicate/hash drift, and selects ExternalData's copy branch.
  Fresh store/generate matrices passed 12/12 and 8/8, including an empty
  override fallback and non-runnable explicit-override isolation. Conan export
  revision `cfd451e43445e075a85bcac7a2fddd1e` contained 15/15 expected files and
  992270 object bytes. The completed CMake probe was reconciled without rerun:
  exact-root positive plus manifest-parent fail-closed negative both passed.
- Exact-current-HEAD CI task `#26212` (global buildid `28929`) failed in
  `checkout-pr` before recipe execution: GitCode's text PR patch omitted binary
  payloads for the newly added CID files and reported `missing binary patch
  data`. The branch now contains canonical 76-column Base64 text only;
  `export_sources()` decodes into its isolated export tree and verifies the
  unchanged manifest path, byte count, and SHA-256 for every object. Directed
  transport tests passed 6/6, exported runtime checks passed 8/8, and fresh
  Conan export revision `272725e9dca1c58a5f9fcdb304dcd52f` contained the same
  15/15 runtime files and 992270 raw object bytes with zero encoded files.
  Replacement CI remains required to prove the platform checkout path.
- Previous authorized-device W3 attempt `20260808T204214Z` is preserved only as
  failed evidence. It exited before Conan because the target shell tried to
  create a here-document temporary file under read-only `/tmp`; no build or
  test count is recorded from that run.
- Non-authoritative Windows sanity: the same option set configured successfully
  in `E:\itkb-192-001`; `itksys` built with Ninja `-j1`. A later native
  `ITKCommon` probe was stopped at the 15 minute local bound and is not counted
  as a pass.
- The patch6-current complete host-runnable upstream test closure configured the patched
  v5.4.6 source with `BUILD_TESTING=ON`, `ITK_BUILD_DEFAULT_MODULES=OFF`,
  `Module_ITKCommon=ON`, `Module_ITKGoogleTest=ON`, `ITK_USE_KWSTYLE=ON`,
  `ITK_USE_CLANG_FORMAT=OFF`, and `ITK_FORBID_DOWNLOADS=ON`. The clean build
  used the fixed local KWStyle source, a manifest-bound 14-object ExternalData
  store, and no URL fallback. Ninja built all 2209/2209 edges and CTest
  executed 618/618 tests with 100% pass rate, failed=0 and skipped=0.
  The exact source preparation applied patch1 through patch6 with strict
  `patch_ng(strip=0, fuzz=False)` and has SHA256
  `d54edcacd9bf600eea1077a4214c470657ff78b0c3150b07ec88833713a10f4e`.
  Inventory SHA256 is
  `b269a30b908fa17cbbb0e63b60115c3016561a1abe3ca7c9526d6bfbde69eff6`;
  raw CTest log SHA256 is
  `7258864c1164f98509b51c6e0aa5fad962f83ff6f34aceb2975a4d990180f438`;
  terminal SHA256 is
  `546cc31b93b3a5ea723cf818a4dd3aa6ec41b69a919c2c97ab04db053092c43b`.
  This host result proves the upstream suite itself; a fresh OHOS W3 must
  still run the same recipe path and installed-package consumer before PR.
---

**编译结束**: 2026-08-15 03:08
**最终状态**: built
