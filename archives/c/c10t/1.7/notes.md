# c10t 1.7 adaptation notes

## Evidence status

- Source version: 1.7 (upstream tag, the current stable release).
- Source SHA256:
  `0e5779d517105bfdd14944c849a395e1a8670bedba5bdab281a0165c3eb077dc`
  (cross-checked against the Homebrew `c10t` formula for tag 1.7).
- Task branch `feat/c10t-1.7` previously carried no `archives/c/c10t/`
  tree, so the HMBS preflight gate reported `incomplete` ("unable to read
  the current archive tree"). This round creates the full recipe tree.
- W3 device evidence is pending: it will be produced by the HMBS preflight
  (`conan create` on the HarmonyOS aarch64 device) after this round.

## Build design

- Application package (R38): only the `c10t` binary is published to
  `bin/`. Upstream ships no `install()` target, so `package()` copies the
  `<build>/c10t` binary directly (CMAKE_RUNTIME_OUTPUT_DIRECTORY equals
  CMAKE_BINARY_DIR; Homebrew does the equivalent `bin.install`).
- The bundled `libs/unc` helper is built in-tree (`BUILD_DEV_LIBS=ON`),
  the same default the Homebrew formula builds with.
- The OHOS patch (`patches/0001-ohos-cmake-and-boost-compat.patch`) is
  generated against the real upstream 1.7 release tarball with byte-exact
  context (tabs in the `execute_process` block, trailing whitespace on
  in-function blank lines); a revision written against assumed content
  failed `apply_conandata_patches` on `src/mc/utils.cpp` in preflight.
- `src/image` / `src/nbt` list `${ZLIB_LIBRARIES}` / `${PNG_LIBRARIES}` as
  `add_library` sources; under Conan CMakeDeps those expand to
  imported-target names (`ZLIB::ZLIB`, ...), which CMake rejects, so the
  patch links them via `target_link_libraries` instead.
- Conan CMakeDeps finds dependencies in CONFIG mode, which leaves legacy
  `*_INCLUDE_DIR` / `*_LIBRARIES` variables empty. Intermediate static libs
  (`c10t-mc` etc.) therefore compiled with no Boost include path
  (`boost/ptr_container/ptr_vector.hpp` not found). The patch propagates
  `INTERFACE_INCLUDE_DIRECTORIES` from any available Boost/ZLIB/PNG/Freetype
  imported target via global `include_directories`, and appends
  `Boost::filesystem` / `Boost::thread` config targets to `c10t_LIBRARIES`.
- `CMAKE_CXX_STANDARD=11` satisfies modern Boost headers (Homebrew passes
  the same flag); `Boost_USE_STATIC_LIBS=OFF` matches the shared Conan
  dependency closure; `CMAKE_POLICY_VERSION_MINIMUM=3.5` accompanies the
  patched `cmake_minimum_required(VERSION 3.5)`.
- Direct requirements are `boost/1.91.0.1` (thread + filesystem; `system`
  is header-only since Boost 1.85), `libpng/1.6.58`, `freetype/2.14.3`
  and `zlib/1.3.1.1` (linked directly as `${ZLIB_LIBRARIES}`, pinned to the
  same revision the published `libpng/1.6.58` closure requires).
- Host `boost/1.91.0.1` is a subset build: its package lacks
  `boost/ptr_container/ptr_vector.hpp` (included by `src/nbt/nbt.hpp`;
  device compile failed with `fatal error: ... file not found`). Following
  the autodock-vina 1.2.7 precedent, the header-only `boost/1.84.0` package
  (complete header set) is added as a build-context header fallback via
  `tool_requires`; linking stays on 1.91.0.1. `generate()` exports both
  include dirs through `C10T_BOOST_INCLUDE_DIRS` (host first) and sets the
  component defines toolchain-wide, and fails closed if neither side
  provides the `ptr_vector.hpp` header.

## Dependency boundary

- `boost/1.91.0.1`: thread + filesystem compiled components used.
- `libpng/1.6.58`: PNG output.
- `freetype/2.14.3`: text annotation rendering.
- `zlib/1.3.1.1`: archive decompression via direct `${ZLIB_LIBRARIES}` link
  (same revision as the published `libpng/1.6.58` closure).

## Test inventory

- Upstream registers zero tests: the top-level `CMakeLists.txt` never
  calls `enable_testing()` / `add_test()`, and `test/` only defines the
  `EXCLUDE_FROM_ALL` `c10t-test` helper (needs `boost_unit_test_framework`,
  intentionally not required). `ctest` therefore discovers 0 tests and
  there is no `make check` target. Full audit in
  `test_package/MANIFEST.yml` (`upstream_tests_exist: false`).
- Four installed-package consumer cases in `test_c10t.sh`:
  1. `c10t --help` exits 0 and prints usage.
  2. `c10t --list-colors` exits 0 and lists block colors (the Homebrew
     formula's own test).
  3. `c10t --version` exits 0 and reports 1.7.
  4. `c10t` with no arguments fails with a usage error (exit != 0),
     proving the harness observes real failures (anti-stub check).

## Evidence boundary

- The committed `built` status means the recipe structure is complete and
  ready for device verification; it does not claim a passed W3 run. The
  authoritative W3/test evidence will be the HMBS preflight log, whose
  `HMBS_TEST_PACKAGE_RESULT` / `HMBS_UPSTREAM_TEST_RESULT` markers are the
  only basis for the PR test-rate fields.

## 2026-09-06 preflight compile fixes (uncommitted, awaiting device re-run)

- `src/image/format/png.hpp:48: Z_DEFAULT_STRATEGY` undeclared: the header
  used the zlib macro via transitive `<png.h>` without including `<zlib.h>`.
  Fixed by appending the upstream commit 800977bb hunk (`#include <zlib.h>`)
  to the existing patch (Homebrew applies the same backport).
- `boost/core/detail/sp_thread_sleep.hpp: pthread_setcancelstate`
  undeclared (x2, via `src/main.cpp`): OHOS musl provides no POSIX
  thread-cancellation API (E127/E085); newer Boost guards the calls behind
  a platform macro the device compiler does not predefine. Fixed without
  touching the dependency and without any platform macro in patches/ or
  `-D` injection: new recipe-owned `compat/ohos_pthread_stub.h`
  (musl-detected `__linux__ && !__GLIBC__`, glibc no-op) redirects both
  cancel calls to no-ops, force-included from `generate()` via `-include`.
- `copy_if_different .../font.ttf ...: No such file or directory` at
  configure time: `build()` now ensures a placeholder source file and the
  build directory exist before `cmake.configure()` (font-dependent runtime
  paths are not exercised by the test_package cases).
- Prior-cycle hypotheses (patch context offset, `ptr_container` subset
  headers, `filename().string()` migration) are closed; this round opens a
  new failure domain (missing transitive include + libc capability gap)
  with a different implementation route (upstream backport + capability
  shim), per the 3-strike rule.

## 2026-09-06 retry: shim never reached the device (delivery fix)

- Second preflight on the same fingerprint still failed with the identical
  `pthread_setcancelstate` errors even though the patch (zlib) applied.
  Export log proves why: `export_sources()` copied only conandata.yml, so
  the recipe-side `compat/ohos_pthread_stub.h` never reached the device
  cache and the `-include` was silently skipped (`except: pass` hid it).
- Different route from the failed attempt: no longer read the shim from
  `self.recipe_folder`; `generate()` now writes the shim text into the
  build folder (`c10t_ohos_pthread_stub.h`), logs the path via
  `self.output.info`, appends plain `-include <abs path>` to both
  `tc.cflags`/`tc.cxxflags`, and warns (instead of passing silently) if
  injection fails. Next preflight log must show the
  `c10t: OHOS pthread shim -> ...` line; if the pthread errors persist
  despite that line, the `-include` mechanism itself (not delivery) is the
  suspect.

## 2026-09-06 retry 2: wrong CMakeToolchain attribute (API fix)

- Third preflight on the same fingerprint finally gave a precise cause:
  `WARN: c10t: pthread shim injection failed ('CMakeToolchain' object has
  no attribute 'cflags')`. The shim file itself was written (the marker
  line printed), but Conan 2.30's CMakeToolchain has no `cflags/cxxflags`
  attributes, so no `-include` ever reached the toolchain file.
- Different route from both prior attempts (delivery, not content):
  use the Conan 2 API names `extra_cflags`/`extra_cxxflags` (with a
  `hasattr` fallback probe to older `cflags`/`cxxflags` names), and raise
  instead of silently passing if neither exists. The marker line plus the
  absence of the WARN line in the next log proves injection happened.

## 2026-09-06 retry 3: patch tail malformed, png.hpp never patched

- Fourth preflight on same fingerprint still reports
  `src/image/format/png.hpp:48: Z_DEFAULT_STRATEGY` undeclared even though
  the patch description claims the zlib.h hunk and `Apply patch` succeeds.
  Root cause in patch file: the png.hpp hunk was appended with `+` prefixes
  inside the `src/players.cpp` hunk (`+diff --git ...png.hpp`), so `git apply`
  inserted 7 literal diff-text lines into players.cpp and never touched
  png.hpp. Different route from prior cycles (which changed shim delivery
  `recipe_folder` -> build folder, then `cflags` -> `extra_cflags`): fix the
  patch tail to a real separate `diff --git` block AND add a programmatic
  fallback in `build()` that inserts `#include <zlib.h>` after `#include
  <png.h>` if the header still lacks it. The pthread shim injection already
  succeeds (marker line present, no WARN in latest log), so it is unchanged.
  Next preflight must show `c10t: ensured <zlib.h> in png.hpp` or a clean
  png.hpp compile plus no `players.cpp` garbage lines.

## 2026-09-06 retry 4: patch stream incomplete (hunk count off by one)

- Preflight failed in export/build before compile: \`apply_conandata_patches\` raised \`Failed to parse patch ... patch stream is incomplete\` on \`0001-ohos-cmake-and-boost-compat.patch\`.
- Root cause in patch tail: png.hpp hunk header \`@@ -2,6 +2,7 @@\` promises 6 old / 7 new lines but file provided only 5 context + 1 addition (missing trailing blank context after \`#include image_base.hpp\`); upstream head confirms lines 2-7 are define/blank/png.h/blank/image_base/blank (6 lines). Conan strict parser and \`git apply --check\` (corrupt at line 229) both reject it.
- Fix (different from retry 3 which split the diff block): keep block split, append the missing blank context line single-space after \`#include image_base.hpp\` so counts match 6/7. Local \`git apply --check\` no longer reports corrupt (only expected missing-file errors outside source tree). build() zlib.h fallback unchanged as defense in depth.
- Readonly-tmp platform diagnosis in same log is harness noise (/tmp sh tmp, /proc cmdline) not recipe writes; recipe uses only build_folder/source_folder, no action.

## 2026-09-06 retry 5: C++17 dynamic exception specifications (compile fix)

- Preflight now passes patch apply and CMake configure; build fails compiling
  src/main.cpp with 3 errors, first shown as
  src/threads/threadworker_impl.hpp:29 ISO C++17 does not allow dynamic
  exception specifications. CMAKE_CXX_STANDARD=11 in recipe did not prevent
  C++17 mode on device clang.
- Root cause: throw(Type) removed in C++17. Four sites in upstream 1.7 use it:
  sync_queue::take and threadworker::internal_work throw(interrupted_exception),
  players_db::read declaration plus definition throw(players_db_exception).
  Empty throw() elsewhere remains valid and untouched. Three of them are
  visible in the main.cpp TU, matching the 3 reported errors.
- Fix (new domain vs retry 4 patch-tail count fix): append three hunks to the
  existing portability patch removing the specs (functions keep throwing,
  spec deletion preserves semantics in all standards). Verified locally by
  downloading the 1.7 tarball and running git apply --check plus git apply:
  all 12 hunks apply cleanly and the throw(Type) strings are gone while
  zlib.h insertion remains.

## 2026-09-06 retry 6: undefined boost_filesystem / FT_* symbols at link (link fix)

- Preflight now compiles cleanly but the final link fails: undefined
  boost::filesystem::detail::directory_iterator_construct plus FT_Init_FreeType /
  FT_New_Face / FT_Set_Pixel_Sizes / FT_Load_Char.
- Root cause: under Conan CMakeDeps CONFIG mode the legacy variables
  (ZLIB_LIBRARIES/PNG_LIBRARIES/Boost_LIBRARIES/FREETYPE_LIBRARY) stay empty,
  and the patch only appended Boost::filesystem/thread to c10t_LIBRARIES, so the
  final target_link_libraries(c10t) line carried no ZLIB/PNG/Freetype input;
  c10t-image/c10t-nbt PUBLIC links used the same empty vars. MODULE-mode
  find_package would additionally resolve system paths instead of OHOS binaries.
- Fix (new domain vs retry 5 compile fix): extend the c10t_LIBRARIES append loop to
  all CONFIG targets (Boost headers/filesystem/thread, ZLIB::ZLIB, PNG/pmg/libpng
  variants, Freetype variants, Threads::Threads); add imported-target fallback loops
  to src/image and src/nbt subdir lists; set CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON in
  generate() so find_package resolves Conan OHOS packages. Verified locally:
  git apply --check plus full git apply against the real 1.7 tarball both succeed
  and the patched subdir files contain the fallback links.
- readonly_tmp platform diagnosis in the same log is harness noise only
  (preflight.sh mktemp, pip chardet warning); the recipe writes solely to
  build_folder/source_folder, no action taken.

## 2026-09-06 retry 7: boost_filesystem still undefined after target append (ground-truth link)

- Second preflight on the same link fingerprint: FT_* errors are gone (Freetype
  CONFIG-target append + PREFER_CONFIG worked) but
  boost::filesystem::detail::directory_iterator_construct is still undefined.
  Different strategy from retry 6 (which only appended more imported-target
  names): the target can exist yet carry no library (in-repo collada-dom
  precedent: a headers-only/stale boost binary leaves exactly these detail
  symbols undefined), so name-guessing cannot converge.
- Fix: recipe generate() now probes the real host boost package lib dir for
  libboost_filesystem / libboost_thread binaries, logs the full dir listing
  (c10t: host boost lib dir ...) plus per-component warnings, and passes found
  absolute paths via C10T_BOOST_LINK_LIBS, which the patch appends to
  c10t_LIBRARIES (absolute paths link regardless of target state; target append
  kept as fallback). Patch also emits message(STATUS C10T c10t_LIBRARIES=...)
  and CMAKE_VERBOSE_MAKEFILE=ON prints the full link command, so the next
  preflight tail proves which boost binaries reach the linker. Rejected
  switching to boost/1.90.0.1 (collada-dom verified, but its Morpheus subset
  lacks thread which c10t requires) and rejected linking build-context 1.84.0
  libs (cross-version header/lib ABI skew).
- Verified locally: py_compile on both conanfiles, git apply --check plus full
  git apply of the patch against the real 1.7 tarball, and a 3-case simulation
  of the probe block (so/a-fallback/missing-dir). VERBOSE flag is temporary
  diagnostics and will be removed once the link line is confirmed.

## 2026-09-06 retry 8: Boost.Filesystem header/lib ABI skew (root-caused fix)

- Third preflight on the link fingerprint finally exposed the full link line
  (CMAKE_VERBOSE_MAKEFILE): libboost_filesystem.so IS linked (twice, absolute
  paths) yet directory_iterator_construct stays undefined, so the published
  1.91 .so genuinely lacks the referenced symbol. Different strategy from
  retries 6-7 (link-target/path plumbing): compare the symbol across versions.
- Root cause, proven byte-exact from upstream sources: 1.84 directory.hpp
  declares directory_iterator_construct(..., unsigned int, ...) while 1.91
  declares (..., directory_options, ...). The device undefined reference spells
  unsigned int, so consumer TUs compiled against 1.84 fallback declarations
  (quoted-include fallthrough from a partial host 1.91 filesystem subtree)
  while linking the 1.91 .so. No target-name or path tweak can fix an ABI mix.
- Fix (version-consistent per-component split): generate() logs a header
  inventory (BOOST_VERSION + directory.hpp presence, host vs fallback),
  shadows ONLY boost/filesystem/** + boost/filesystem.hpp from the complete
  1.84 fallback into the build dir (copies, HMDFS-safe) first in
  C10T_BOOST_INCLUDE_DIRS, links thread by absolute 1.91 path, and links the
  device-verified 1.84 libboost_filesystem.a (upstream foreach/path tests pass
  on OHOS) via C10T_BOOST_FS184_LIB PUBLIC from c10t-mc (correct static
  placement). Rejected boost/1.90.0.1 (Morpheus subset lacks thread) and
  linking build-context 1.84 libs under 1.91 headers (same skew class).
- Self-caught editing incident in this round: the new src/mc block was first
  appended with + prefixes on its diff headers (retry-3 class error), which
  git apply --check silently accepted while --stat omitted the file. Lesson:
  --check alone is not a gate; always require --stat to list the touched file
  plus full apply plus content read. Rewrote the tail byte-precise in python
  (hunk @@ -1,10 +1,19 @@) and re-verified all three gates plus players.cpp
  cleanliness. Top hunk recount 43->44 for the added FS184 STATUS line.
- Verified locally: py_compile, --check/--stat/full-apply/content-check vs the
  real 1.7 tarball, and a simulation of inventory+shadow+probe (host-missing
  directory.hpp detected, 3 shadow files, order shadow;host;fallback).
  VERBOSE kept one more round to confirm the fixed link line.

## 2026-09-06 retry 9: test_package loader env + lax negative control (harness fix)

- Preflight built and linked cleanly but test_package reported 1/4:
  `--help`, `--list-colors`, `--version` all "exited non-zero", while the
  bare-invocation control PASSED. New domain vs retries 1-8 (all were
  compile/link issues); the binary itself was never the suspect.
- Root cause (two harness bugs, proven from upstream source + log):
  (1) test() ran `self.run(cmd, env=None)`, so the musl loader never got
  the VirtualRunEnv run paths (LD_LIBRARY_PATH) for the shared Conan libs
  (libboost_thread.so, libpng, freetype, zlib) and aborted every
  invocation with "Error loading shared library ..." before main() ran.
  Repo precedent is unanimous: daemon/aamath/fzy/b2sum test_packages all
  use env="conanrun". (2) Case 4 grepped `usage|error|require`, but the
  genuine bare message (`No action specified, please type ...`, main.cpp
  exit_error path) contains none of those words -- so the observed PASS
  could only have come from the loader's own "Error ..." line. A binary
  that never reached main() spuriously passed the anti-stub control.
- Fix: `self.run(..., env="conanrun")` with C10T_BIN/TMPDIR/TMP/TEMP
  inline in the command (b2sum precedent, immune to env-merge semantics);
  case 4 now requires the exact app message `no action specified`
  (strictly stronger, loader text cannot match); each case captures
  `rc=$?` and dumps a bounded output excerpt on failure so the next log
  distinguishes loader failures (e.g. rc=127) from app errors. No
  assertions removed, no tests skipped; controls are stricter than before.
- Local gates: py_compile on both conanfiles; harness self-check
  (RESULT trailer intact, conanrun present, no active env=None, strict
  case-4 pattern, rc capture, no hardcoded /tmp writes).
