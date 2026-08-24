# librasterlite2 1.1.0-beta1 adaptation notes

## Scope

- `1.1.0-beta1` is the official RasterLite2 upstream pre-release archive. It
  must not be described as stable `1.1.0`.
- The package is a real prerequisite for the spatialite-gui dependency graph,
  which requires RasterLite2 `>= 1.1.0`.
- Only this version directory is owned by this task worktree.

## Source and W0

- Official URL: `https://www.gaia-gis.it/gaia-sins/librasterlite2-sources/librasterlite2-1.1.0-beta1.tar.gz`
- SHA-256: `f7284cdfc07ad343a314e4878df0300874b0145d9d331b063b096b482e7e44f4`
- Carried W0 baseline: `F:\HarmonyPC\librasterlite2-110b1\w0-after-main-02`.
  It is dependency evidence from the unchanged requirements, not the final
  current-tree authority.
- W0 settings: OHOS, armv8, clang 15, libc++, Release; `--build=never`.
- W0 graph: 25 package nodes; 24 Download nodes and one legitimate OpenSSL
  Skip node. All resolved nodes have RREV/PID/PREV, `binary_remote=ohpcd`,
  empty `info_invalid`, and package folders under the private F-drive Conan
  home. The exact current-tree graph, dependency downloads and independent
  verification are bound outside the staged tree by SHA-256 in the active
  W3 preparation's `W0-BINDING.json`; any staged edit requires a fresh binding.

## Adaptation decisions

- `config.guess` has an opt-in `CONFIG_GUESS_USE_CC_DUMPMACHINE=1` path. It
  returns the compiler-proven tuple and fails closed on a missing or empty
  compiler result; it does not guess from an OHOS or HarmonyOS uname string.
- `config.sub` accepts and preserves `linux-ohos`, including both
  `aarch64-linux-ohos` and `aarch64-unknown-linux-ohos` inputs.
- Generated Autoconf temporary directories are rooted at `TMPDIR`. The two
  configure-created `confXXXXXX` directories use `umask 022`, which is
  required for continued HMDFS writes; `TMPPREFIX` points to a writable
  `zsh-tmp-` prefix inside the task-local build directory.
- OHOS configure probes are compiled with the profile's exact absolute C
  compiler and signed before configure continues. Build and test actions are
  serial (`-j1`), and target ELF outputs are signed before execution.
- The target toolchain uses `-fsigned-char` for all C translation units.
  Upstream uses plain `char` and `char *` for semantically signed INT8 raster
  samples; keeping one compiler mode preserves the upstream negative-value API
  behavior without changing source, test expectations, or byte layout.
- The ASCII Grid reader needs a seekable temporary stream. On the real target,
  libc `tmpfile()` returns `EACCES` and does not honor the task-writable
  `TMPDIR`, while `mkstemp()` succeeds in that same directory. The source patch
  retains `tmpfile()` as the first choice and, under the existing POSIX header
  capability, falls back to `TMPDIR/mkstemp`, immediately unlinks the pathname,
  wraps the still-open descriptor with `fdopen("w+b")`, and closes the
  descriptor if wrapping fails. It has no OHOS or HarmonyOS source macro.
  This is a package-specific application of the existing reusable E320
  `tmpfile()` capability-fallback pattern, so this PR does not submit a
  duplicate E2156 draft pair.
- Shared library aliases are rejected on OHOS; package metadata exports the
  stable unversioned `librasterlite2.so` and `mod_rasterlite2.so` names.

## Test inventory

- `test/Makefile.am` registers 71 Automake tests; this is the authoritative
  upstream count.
- `test/sql_stmt_tests` contains 722 `.testcase` files and
  `test/sql_stmt_security_tests` contains 657, for 1,379 embedded SQL
  scenarios. The two `Makefile.am`/`Makefile.in` files in those directories are
  not testcases.
- The consumer source exercises version, target CPU, codecs, pixel/palette,
  raster and section ownership APIs with 14 assertions. It is not a substitute
  for the upstream suite.

## Current validation boundary

The immutable r196 product closure is the current runtime authority. Its one
real-device launch completed the full upstream inventory at `71/71`, one
package-consumer flow with `14/14` assertions, runner RC 0, cleanup PASS, and
closed ownership. It was not replayed. The R218 current-main rebind at
`250c1906b6fb844d1969e4dbd7c4f714014f4372` independently proves that all
16 W3-bound runtime inputs (15 candidate files plus the profile), all 24
dependency provider tuples, the recipe, build policy, and test denominators
remain identical to r196.

The authoritative patch replay used Conan 2.29.1's `patch_ng` applicator with
`fuzz=False` on a fresh extraction at
`F:\HarmonyPC\librasterlite2-110b1\patch-replay-20260819-15`. All four target
files changed, retained LF line endings, and passed final semantic checks. A
fresh current-main W0 resolves every active provider through `ohpcd` with
`--build=never`. Knowledge and report edits do not alter the runtime closure;
any later recipe, patch, dependency, profile, build-flag, target-binary, or
test-denominator change invalidates the r196 reuse boundary. W4, the Pre-PR
contract, Issue/PR binding, Review, CI, and submission remain separate
current-snapshot gates. No Conan/CNB upload has been performed. The failed
r25-r107 device attempts below remain immutable historical diagnostics; R218
does not claim to have independently revalidated every predecessor artifact.

## W3 successor diagnostics

- r25 reached the real device and closed cleanly with `launch_count=1`, but
  Conan failed before configure because the skipped `openssl/3.5.6.1` node had
  an empty `dependency.package_folder`; `_environment()` now skips empty package
  folders before constructing `lib/pkgconfig` paths.
- r26 reached configure and closed cleanly with `launch_count=1`. The published
  `lz4/1.10.0` package materialized `liblz4.a` and Conan metadata but no
  `liblz4.pc`, so the upstream `LIBLZ4` pkg-config probe failed. The recipe now
  generates a task-local compatibility `liblz4.pc` only when the real library
  exists; it does not add a source alias or fabricate a binary.
- r27 reached the real `conan create` generate phase and closed with
  `launch_count=1`, cleanup PASS and `ownership_closed=true`. Conan 2 exposes
  the dependency version through `dependency.ref.version`; accessing the
  nonexistent `dependency.version` raised `AttributeError` while generating
  the compatibility `liblz4.pc`. The recipe now uses the reference-bound
  version and r27 remains replay-forbidden.
- r28 reached configure and closed with `launch_count=1`, cleanup PASS and
  `ownership_closed=true`. All compiler and pkg-config probes passed, but
  `config.status` could not create `tmp/conff*/subs1.awk` on HMDFS because
  the configure temporary-directory patch retained `umask 077`. The patch
  now narrows the HMDFS compatibility change to `umask 022` at both
  `confXXXXXX` creation sites; r28 is replay-forbidden.
- r29 closed with `launch_count=1`, cleanup PASS and
  `ownership_closed=true` before configure. The first `umask 022` replacement
  applied, but the second had accidentally been encoded as unchanged patch
  context, so patch-ng required a nonexistent 022 source line and rejected the
  hunk. The patch now represents both sites as explicit `-077/+022` pairs;
  r29 is replay-forbidden.

- r30 reached the real device and consumed `launch_count=1`, cleanup PASS and
  `ownership_closed=true`. Compilation stopped at
  `headers/rasterlite2_private.h:389:2: error: unknown type name 'time_t'`;
  OHOS libtiff headers did not provide this standard type transitively. The
  r31 successor adds an explicit portable `#include <time.h>` patch, with no
  OHOS conditional macro. r30 is immutable and replay-forbidden.

- r47 completed the real upstream inventory with `launch_count=1`, cleanup
  PASS and `ownership_closed=true`, but only 47 of 71 tests passed. The detailed
  log showed expected signed INT8 values `-120` and `-17` being observed as
  `136` and `239`. Upstream `test11.c` and TIFF output tests use plain `char`
  for these values; the successor applies `-fsigned-char` consistently through
  the Conan toolchain. Upstream source and test expectations remain unchanged,
  and r47 is immutable and replay-forbidden.

- r49 completed the same real 71-test inventory with `launch_count=1`, cleanup
  PASS and `ownership_closed=true`. The consistent signed-char mode repaired
  23 of r47's 24 failing tests and produced `70/71`; only `test_map_ascii`
  remained. Its failure predates the signedness fix. r49 remains immutable and
  replay-forbidden; later target evidence disproved fixture restoration as the
  root-cause repair.

- r55 completed the real 71-test inventory on the exact `bb66e116...` staged
  tree with `launch_count=1`, cleanup PASS and `ownership_closed=true`. It
  again produced `70/71`; the only failure was `test_map_ascii` with
  `LoadRastersFromDir "grid_8_none_256" error: (null)`. r55 proves that
  restoring only `ascii2.asc` is insufficient. r55 is immutable and
  replay-forbidden.

- r65 restored both audited ASCII fixtures, verified each as a strict
  `600x600` grid with no illegal token, and still completed at `70/71`; the
  sole failure remained `test_map_ascii`. This target run disproves the fixture
  restoration hypothesis, so the recipe no longer changes either fixture.
  r65 is immutable and replay-forbidden.

- r68 isolated the actual target capability boundary: libc `tmpfile()` failed
  with `errno=13` even with a writable task `TMPDIR`, while `mkstemp()` in that
  directory passed. r70 then proved the full replacement lifecycle on the same
  target: `mkstemp`, immediate unlink of the open descriptor, `fdopen`,
  write/read/rewind, close, and final pathname absence all passed. These probes
  validate the fallback primitive; a fresh complete W3 is still required to
  prove `71/71` and the 14-assertion consumer on the final staged tree.
