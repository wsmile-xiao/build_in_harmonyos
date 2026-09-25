# kconfig-frontends 4.11.0.1

## Scope

Package the Kconfig parser library and the `conf`, `mconf`, and `nconf` text
frontends for Linux and HarmonyOS PC arm64. GTK/Qt frontends and upstream helper
scripts are disabled. The package uses the official GitLab repository pinned to
commit `f22fce3a308be1c7790ebefc6bbedb33c5f7c86a`; its `.version` marker resolves
to release `4.11.0.1`. `conandata.yml` stores the SHA256 of the unprefixed
`git archive --format=tar` snapshot at that commit. The Conan source step
recreates and checks that canonical snapshot after checkout.

## Dependencies

The build uses the published Conan recipes for `ncurses/6.6`, `autoconf/2.72`,
`automake/1.18`, `libtool/2.5.4`, `m4/1.4.19`, `bison/3.8.2`, `flex/2.6.4.2`, and
`gperf/3.3`. The ncurses dependency is forced static to avoid shadowing the
HarmonyOS system curses library. Remote `conan download --only-recipe` checks
passed for all eight references before implementation.

## Upstream tests

The pinned Git tree contains no `tests/` directory, no test-named source files,
and no Automake `TESTS` or `check_PROGRAMS` registration. The recipe still runs
the upstream `make check` target when the build can execute on the target; this
is only a build-system check and will not be counted as functional upstream
coverage. The Conan consumer test supplies functional coverage by calling the
installed parser API, generating and preserving `.config` values with
`kconfig-conf`, and opening/exiting both curses text frontends through a PTY.

## HarmonyOS-specific coverage

On the OHOS profile, the consumer requires the resolved `$HOME` to be below
`/storage/Users`, then runs the parser and `kconfig-conf` with the configuration
output under `$HOME/tmp` and confirms the file is readable and contains the
expected values. This exercises the writable HMDFS-backed HarmonyOS user-home
path rather than relying on `/tmp`.

## Validation record

Validated on 2026-09-24 in the HarmonyOS 6.0 PC VM (AArch64/armv8, Clang 15,
Conan 2.29.1) with the `ohos-aarch64` host and build profiles.

- Conan `create` passed, including the package build, `make check`, and the
  consumer test package. The pinned upstream tree has no registered test cases;
  the `make check` target was still executed.
- The consumer linked and called the parser API, checked `conf` defaults and
  saved-value preservation, and opened and exited both `mconf` and `nconf` in
  PTYs. All 19 declared assertions passed.
- The HarmonyOS-specific checks passed: `$HOME` resolved below
  `/storage/Users`, and config read/write succeeded under `$HOME/tmp` (4
  HarmonyOS assertions).
- Conan Verify G1–G4 passed. W3 local CI passed with exit code 0; the generated
  local `.ci-result.json` integrity value and W3 log SHA256 were verified.
- The build log confirms that the recipe restored execute bits on 10 known
  Autotools helper scripts. Conan Verify still emits the E490 advisory because
  its current risk checker does not recognize this mitigation; the clean build,
  `make check`, and consumer tests all passed with the mitigation active.

The test counts and final results are summarized in this note and in the PR
description; generated build logs and runtime markers remain local.
