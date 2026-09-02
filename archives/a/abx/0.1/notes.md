# abx 0.1 HarmonyOS pre-adaptation notes

## Current status

- Issue: 2242
- Branch: `feat/abx-0.1`
- Status: all direct dependencies are published. The recipe, package,
  signature, and expanded installed-binary test package passed an isolated
  device integration prevalidation (37/37). Formal CI #36495 reached the
  Autotools compiler probe and exposed the SDK lld runtime-path issue described
  below; the next CI run must confirm the fix and complete L1-L5.
- Worktree: `D:\harmonyos\worktrees\abx-667`

## W0 dependency check

The latest check used the required command form
`conan download <ref> -r=ohpcd --only-recipe` on the HarmonyOS device on
2026-08-19. Conan 2.29.1 ran from an isolated `CONAN_HOME` under
`/storage/Users/currentUser/ohpc-ci-shadow/w0-abx-20260819T052321Z-1275` while
holding the global Shadow device lock.

| Reference | Result | Evidence |
|---|---|---|
| `glib/2.84.0.1` | published | Recipe revision downloaded successfully. |
| `automake/1.18` | published | Recipe revision downloaded successfully. |
| `gtk/3.24.38` | PR open | Canonical R42-safe coordinate passed Shadow CI; adaptation PR #5782 is open and the recipe is not yet published. |
| `libsndfile/1.2.2` | PR open | Adaptation PR #5578 is open after Shadow CI pass; the recipe is not yet published. |
| `portaudio/19.7.0` | PR open | Adaptation PR #5739 is open after formal CI and AI review passed; the recipe is not yet published. |
| `abx/0.1` | unoccupied | The target recipe did not download; recheck before submission because publication state can change. |

The same remote successfully downloaded GLib and Automake immediately after the
three failures, so the failures are not a general connectivity outage. Per R36,
do not run formal Shadow CI or submit abx until the three missing runtime
dependencies are merged and published by their own issues and PRs.

Update on 2026-09-02: `gtk/3.24.38`, `libsndfile/1.2.2`, and
`portaudio/19.7.0` have all been merged, published, and accepted by the formal
CI dependency gate. The table above is retained as the dated W0 record rather
than the current dependency state.

## Source and build-system analysis

- Upstream project: audio ABX testing application by Petteri Hintsanen.
- Version 0.1 release date: 2016-12-15.
- Authoritative source: Debian's pristine upstream orig tarball, backed by a
  signed `.dsc`; SHA256 is pinned in `conandata.yml`.
- Build system: GNU Autoconf/Automake (`configure.ac`, `Makefile.am`).
- Product: one executable, `bin/abx`; no public library or headers.
- Original dependencies: GLib threads, GTK2, libsndfile, PortAudio V19.
- HarmonyOS strategy: apply Debian's GTK3 port, replace obsolete `glib.m4`
  discovery with `gthread-2.0` pkg-config, regenerate Autotools files, and
  supply dependency `.pc` files through Conan `PkgConfigDeps`.
- On HMDFS the automake/aclocal Perl entry points are invoked explicitly with
  SDK Perl, generated `configure` is run through `/system/bin/sh`, and the
  embedded config.status 0700 temporary-directory pattern is relaxed.
- The installed `bin/abx` is self-signed and its `.codesign` section is checked
  before packaging completes.
- Formal CI #36495 failed while Autoconf checked whether the C compiler could
  create an executable. The active OHOS SDK lld dynamically loads the matching
  `libxml2.so.16` from the SDK `llvm/lib` directory; the recipe now prepends
  that version-discovered directory to `LD_LIBRARY_PATH` for configure, build,
  and install. This is the same SDK runtime requirement exercised by the
  published GTK 3.24.38 recipe and its successful CI #33952.
- The build is native OHOS/aarch64. No `--build`, `--host`, or `--target`
  cross-compilation triplet is injected.
- Autotools temporary files use a build-local `TMPDIR`; make is limited to one
  job to avoid HMDFS FIFO/jobserver issues.

## Patch provenance

- `0001-port-to-gtk3.patch` is Debian's `gtk3.patch` from
  `abx_0.1-0.1.debian.tar.xz` (author Yavor Doganov, last updated 2024-01-11).
- `0002-use-pkg-config-for-glib.patch` replaces the obsolete
  `AM_PATH_GLIB_2_0` macro with `gthread-2.0` pkg-config lookup.
- `0003-add-version-option.patch` adds the application version option.
- `0004-defer-display-open.patch` registers the GTK option group without opening
  a display; normal GUI execution still opens it later through `gtk_init()`.
- `0005-handle-headless-options-early.patch` handles the single-argument version
  and help paths with standard C before any GOption/GTK work. This avoids the
  device-observed futex wait while retaining the real application option names.
- `0006-fix-trial-index-bounds.patch` rejects index `ntrials`; the original
  checks allowed one-element-past-the-end access to the answer/guess arrays.
- `0007-add-runtime-self-test.patch` adds an installed-binary self-test over
  real sound-file I/O, ABX trial/statistics code, GTK3 objects, and PortAudio.
- `0008-preserve-seek-precision.patch` fixes `seek_sound_file()` returning
  fractional seconds through an integer `sf_count_t`, which truncated seeks
  below one second to zero.

## Test inventory and trimming

Upstream 0.1 contains no automated test suite. `src/test.c` is production code
for ABX trial state and binomial p-value calculation, not a test harness.
Neither Automake file defines `TESTS` or `check_PROGRAMS`, so the recipe does
not present an empty `make check` as test coverage.

The consumer test executes the installed binary and records 37 assertions in
four scenarios. CLI checks cover package presence, permissions, exact version,
usage, and four option lines. Deterministic stereo PCM fixtures then drive production
libsndfile metadata/read/seek/close paths, eight ABX trials, guess roundtrips,
array upper-bound rejection, and the exact binomial p-value. A headless GTK3
list model and PortAudio initialization/inventory/termination are exercised,
and mismatched-duration plus malformed-audio fixtures must fail closed.

The current `portaudio/19.7.0` package reports `host_apis=0` and `devices=0`.
The test validates that state is internally consistent; it does not claim
speaker playback or a HarmonyOS audio backend.

## Validation

Local preparation checks passed for source SHA256, eight sequential patches,
application, Python AST parsing, YAML parsing, Conan recipe load/export, shell
syntax, text format, and change scope.

An isolated device integration prevalidation also passed on 2026-08-19:

- run root:
  `/storage/Users/currentUser/ohpc-ci-shadow/abx-r10-0819`;
- working-tree input SHA256:
  `b4fced911d8f26d4610784393e979c49a2329a7b88806f074493d77676f9181d`;
- `conan create` and test_package exit: 0;
- log SHA256:
  `da9fb4f0ee8f919e6e2389ae58d1e93a5f860591a705435750d6e7bd05f3e4c7`;
- packaged arm64 ELF SHA256:
  `2351870532e510c81f4e6df86026b268119fe7c2d3110d063b14b48ad5517cd6`;
- `.codesign` sections: exactly 1;
- test_package: 37/37 assertions passed;
- runtime summary: `gtk=3.24.38`, `portaudio-host-apis=0`,
  `portaudio-devices=0`.

This was a diagnostic integration run using isolated cache copies of the
already validated GTK, libsndfile, and PortAudio PR artifacts. It is not the
required R36 publication check, formal Shadow CI, L0-L5 summary, or publication
evidence. See `reports/device-integration-prevalidation.md`.

## Required next steps

1. Run exactly one package in formal CI after applying the SDK lld runtime-path
   fix and confirm configure proceeds past the compiler executable probe.
2. Confirm `Build Summary: Total: 1`, L0/L1 pass, CLI L2 pass, reviewed L4,
   and a real `bin/abx` artifact at L5.
3. Merge the validated PR and verify the release pipeline publishes
   `abx/0.1` to the public Conan registry.

Formal reproduction command:

```sh
CI_PACKAGES="archives/a/abx/0.1" zsh ci/conan/build_and_test.sh
# or
/path/to/run-ohos-shadow-ci.sh archives/a/abx/0.1
```
