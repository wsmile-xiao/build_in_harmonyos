# NUT 2.8.5 Test Report

## Local pre-adaptation checks

- Source archive SHA256 matches the official checksum:
  `18bf32e59eb764b13da3c4fa70384926d7fa584cb31d2fe7f137a570633eeec1`.
- `conan inspect` parses the package recipe and test package.
- `conan graph info` passes with a local Linux/Clang graph and reports no
  external Conan dependencies for the selected `dummy-ups` scope.
- Python AST parsing passes for both Conan recipes.
- YAML and JSON parsing passes for `conandata.yml`, `manifest.yaml`,
  `test_package/MANIFEST.yml`, and `commands.json`.
- All eight portability patches pass `git apply --check --unidiff-zero` and
  Conan's `patch_ng` application against the extracted NUT 2.8.5 source.
  Applying them to a clean scratch extraction produces the expected HarmonyOS
  and HMDFS changes.

## Shadow CI device validation

Run:

`codex-2.8.5-nut-2.8.5-20260911-conan-20260911-233949-48628`

Result: `PASS` (exit code `0`)

The standard runner completed the following gates:

- `conan create`: passed.
- Upstream `make -j1`: passed.
- Upstream `make check -j1`: passed; the generated default Automake test
  list ran 4 tests, with 4 passed, 0 failed, and 0 errors:
  `nutlogtest`, `nuttimetest`, `nutbooltest`, and `driver_methods_utest`.
- The release archive also contains optional upstream tests that were not
  enabled in this minimal software-core profile: USB tests
  (`getvaluetest`, `getexponenttest-belkin-hid`), the GPIO test (`gpiotest`),
  and the CppUnit test driver (`cppunittest`). The NUT Integration Testing
  suite under `tests/NIT/nit.sh` is present but was disabled with
  `--disable-check-NIT`; the device log records its `make check` entry as
  `NO-OP`. These tests are not included in the 4/4 executed-test pass rate.
- Package validation: passed; `bin/upsc` and `bin/upsd` were present.
- `test_package`: passed; `upsc -V` reported NUT 2.8.5, `upsc -h`
  reported usage text, and `upsd --version` reported NUT 2.8.5. The revised
  consumer script completed eight assertions.
- L0, L1, L2, and L5: passed.
- L4: warning only; the scanner flagged the intentional OHOS `getpass`
  fallback in patch 0004.

The runner also emitted non-blocking warnings for `upslog`, `upssched`, and
`upssched-cmd` version/help probes. These commands are outside the required
client smoke path and the runner still recorded `L2_RESULT=pass`.

Package reference:

`nut/2.8.5#d39703f7c344bc45beb2f39d0d43089a:6b129b068851896169fae42d399fa922d239ce8a#e3e486d055572a7f2263fdea09c8ab9e`

## AI-review follow-up

AtomGit CI build `44728` tested the first review-fix revision and failed
during configure before compilation:

`config.status: ./conf*/subs1.awk: Permission denied`

The failure showed that restoring `umask 077` for the generated configure
script was not compatible with the HMDFS `linux-ohos` scratch directory.
The follow-up revision scopes `umask 022` to that host-specific
`config.status` scratch path and leaves `077` unchanged for other hosts.
AtomGit CI build `44802` then passed all workflow steps, Conan
`test_package`, L0, and L1. Its cleanup step emitted only non-blocking
infrastructure warnings about `buildbot.tac` and HOME path normalization.
Those warnings are outside this library PR's permitted scope. Its summary does
not expose a separate L4 result;
the earlier L4 warning was tied to the superseded platform-macro fallback.

## Path B candidate evidence

The reusable contribution is documented in
`knowledge/drafts/DRAFT-nut-autotools-ohos-upstream-check-chain.{kv,md}`.
It covers the combined OHOS workflow for auditing generated Autotools rules,
keeping HNP build tools visible during `make check`, and validating the actual
Conan package layout from a consumer test. This is distinct from the existing
single-pattern entries for `config.guess`, HMDFS umask, symlink handling, and
`getpass`.

The draft is submitted as a Path B candidate; final B-class recognition remains
subject to project review.

## Remaining scope

This run validated the package build and client/daemon layout. It did not
connect a UPS device or perform a standalone long-running daemon session;
that is outside the dependency-free `dummy-ups` smoke test and can be done in
a later device window if required.
