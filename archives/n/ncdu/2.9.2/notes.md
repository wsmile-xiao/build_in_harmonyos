# ncdu 2.9.2 HarmonyOS adaptation notes

## Scope and source

- Issue: `https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2233`
- Adaptation path: Path A (base adaptation) plus Path B (knowledge extension
  candidate).
- Upstream project: `ncdu` 2.x (the Zig rewrite). The upstream project, output
  binary and manual page are all named `ncdu`; only the 2.x branch is informally
  called "ncdu 2" on the project website (`https://dev.yorhel.nl/doc/ncdu2`).
- Official release: `https://dev.yorhel.nl/download/ncdu-2.9.2.tar.gz`
- Verified SHA-256: `e91135281cb66569f2ca4c0bac277246991e7e52524c0ca8cba3de5c8e81cec9`.
- Build system: Zig `build.zig`; the bundled Makefile is only a convenience wrapper.

## Package identity

The package is `archives/n/ncdu/2.9.2` with `name = "ncdu"`, matching the
upstream project name and the task branch `feat/ncdu-2.9.2` required by CI gate
L0n (R40: the branch base must equal `<package dir>-<version>`).

An earlier round packaged the same 2.9.2 sources under the invented name
`ncdu2` (merged as MR !6465, published as `ncdu2/2.9.2`). That name exists only
to distinguish the Zig rewrite from the C implementation of ncdu 1.x; it is not
an upstream name. That directory has been removed in this branch and replaced
by `ncdu`. Aside from the package name, the recipe and test logic are unchanged.

## Dependency analysis

Required runtime/link dependencies:

- `ncurses/6.6`: published on the `ohpcd` Conan remote.
- `zstd/1.5.7.1`: published on the `ohpcd` Conan remote.

Required build dependency:

- Upstream explicitly supports Zig 0.14 or 0.15, so the published
  `zig/0.16.0` / `zig/0.16.0.1` packages cannot substitute.
- `zig/0.15.2` was adapted independently (issue #2235, PR #5562) and is now
  published on `ohpcd` (recipe revision
  `501adb6c2fb136f4a58e15a2cb2d2412`, package ID
  `876049f3ae10a4560da345bb02378e03e212bc8c`). The earlier W0 blocker is
  resolved.
- The recipe declares `tool_requires("zig/0.15.2")`, which now resolves from
  the remote without a locally exported compiler.
- Zig is a real build requirement, but its issue classification and knowledge
  contribution remain independent from this ncdu Path B application.

The dependency is not vendored or downloaded from this recipe. Doing so would
mix the Zig adaptation into the ncdu PR and violate the dependency split rule.

## Intended build and packaging

- Use Conan dependency package roots through Zig `--search-prefix` for both
  ncurses and zstd; do not depend on interactive-shell `CFLAGS`, `LDFLAGS`, or
  `PKG_CONFIG_PATH`.
- Use isolated global/local Zig caches under the Conan build folder.
- Build with one job and `ReleaseFast`, then run the upstream `zig build test`
  step in the same recipe.
- Install `bin/ncdu`, `share/man/man1/ncdu.1`, and the upstream REUSE license
  files.
- Sign the final ELF with `binary-sign-tool` on OHOS. The validated Zig 0.15.2
  tool package signs generated Zig build/test runners and retries the original
  command after HarmonyOS `AccessDenied` failures.

## Tests

Static source inventory found 13 Zig unit-test declarations across seven
source files. The recipe retains the complete upstream `zig build test` target.

The consumer test is non-interactive and checks the installed program by:

1. asserting exact `ncdu 2.9.2` version output;
2. asserting the help output exposes JSON export mode;
3. scanning a deterministic fixture with `-0 --apparent-size -o`;
4. parsing the exported JSON and checking format version, file names, and exact
   apparent sizes.

A Conan graph resolves `ncurses/6.6` and `zstd/1.5.7.1` (host) plus
`zig/0.15.2` (build) entirely from `ohpcd`; see the re-verification section
below.

## L0k commands.json

`ncdu` is a command-line application, so repository gate L0k requires a
software-level `archives/n/ncdu/commands.json`. This branch provides it with
`type = "tool"`, `name = "ncdu"` and version `2.9.2`.

## Path B knowledge-extension candidate

The ncdu-specific reusable contribution is intentionally separate from the
signed-launcher and generated-ELF support submitted by Zig PR #5562:

1. Bridge Conan dependency package roots into a Zig application build with
   repeated `--search-prefix` arguments. This lets Zig discover ncurses and
   zstd from immutable Conan packages without relying on interactive-shell
   `CFLAGS`, `LDFLAGS`, `PKG_CONFIG_PATH`, or a host filesystem layout.
2. Run the complete upstream `zig build test` target with the same dependency
   prefixes and isolated Zig caches used by the release build. All 13 upstream
   declarations execute on HarmonyOS rather than being silently pruned for a
   cross-build.
3. Validate a terminal-oriented application without a pseudo-terminal by using
   its machine-readable export mode. The consumer test verifies exact version
   and help output, scans a deterministic fixture, parses JSON, and checks file
   names and apparent sizes.

This pattern is reusable for other Zig command-line applications that consume
native Conan libraries or whose interactive UI is unsuitable for unattended
device CI. The evidence, failure evolution, non-claims, and rerun commands are
recorded in `reports/path-b-candidate.md`.

## Local verification (2026-09-11)

Checks performed locally on Windows with the OHOS-adapted Conan 2.29.1:

- Source archive SHA-256 re-confirmed as
  `e91135281cb66569f2ca4c0bac277246991e7e52524c0ca8cba3de5c8e81cec9`,
  matching `conandata.yml` and `manifest.yaml`.
- Source inventory re-confirmed: 13 Zig `test` declarations across 7 source
  files; upstream requires Zig 0.14/0.15 only.
- `conan graph info` with `ci/conan/profiles/ohos-aarch64` resolves
  `ncurses/6.6`, `zstd/1.5.7.1` (host) and `zig/0.15.2` (build) from `ohpcd`
  with no local dependency cache.
- Static checks pass: `conanfile.py`, `test_package/conanfile.py` and
  `test_package/test_ncdu.py` compile; `conandata.yml`, `manifest.yaml` and
  `test_package/MANIFEST.yml` are valid YAML; `git diff --check` is clean.

Not performed locally: `conan create` cannot run on Windows because the
`zig/0.15.2` build requirement and the target toolchain are aarch64/OHOS
binaries.

## Device shadow CI

### Current run under the ncdu identity (2026-09-11, PASS)

The renamed package `archives/n/ncdu/2.9.2` was re-run through the standard
shadow pipeline on the HarmonyOS aarch64 device. Result: exit code 0,
"All packages built and tested successfully".

```text
run_id=20260911T022038Z-c61fe5a0fe-15133
G0_RESULT=pass      (540 knowledge entries, root whitelist passed)
L0_RESULT=pass      all quality gates, including:
                    - L0i: ncurses/6.6, zig/0.15.2, zstd/1.5.7.1 all in registry
                    - L0j: version not in registry yet (first publish)
                    - L0k: commands.json valid (type=tool)
                    - L0m: directory structure valid
L1_RESULT=pass      test_package executed; L1e negative test confirmed
L2_RESULT=pass      ncdu --version OK
L4_RESULT=pass      no patches
L5_RESULT=pass      bin/ has content
KC_RESULT=pass      knowledge check
JC_RESULT=pass      junk check
Total: 1  Success: 1  Failed: 0  (pass rate 100.0%)

  1/13 main.test.imports...OK            8/13 ui.test.shorten...OK
  2/13 main.test.argument parser...OK    9/13 ui.test.fmtsize...OK
  3/13 model.test.entry...OK            10/13 util.test.fmt5dec...OK
  4/13 json_import.test.JSON parser...OK 11/13 util.test.strnatcmp...OK
  5/13 bin_reader.test.CBOR int...OK    12/13 exclude.test.parse...OK
  6/13 bin_reader.test.CBOR string...OK 13/13 exclude.test.Matching...OK
  7/13 bin_reader.test.CBOR skip...OK
  All 13 tests passed.

llvm-objcopy --remove-section .codesign <...>/zig-out/bin/ncdu
binary-sign-tool sign -inFile <...>/ncdu -outFile <...>/ncdu.signed -selfSign 1
package(): Packaged 1 file: ncdu | 1 '.1' file: ncdu.1 | 1 '.txt' file: MIT.txt
Full package reference:
  ncdu/2.9.2#994731c20d2b252b373d6cf41d267438:
  b20ef63da03b6c8ae4b9b3674a4351bf36017117:
  92c626b497f9de8d910cb5314b2f5341
test_package: ncdu consumer test passed: version, help, scan, and JSON export
```

L0j is worth noting: it reported "first publish", confirming `ncdu/2.9.2` is a
new package identity rather than a mutation of an already-published version.

### Prior run under the ncdu2 identity (2026-09-11, PASS)

Before the rename, the same recipe logic — differing only in the package name —
also passed the full pipeline (run-id `20260911T015410Z-d6f07603ad-4795`,
exit 0). This is consistent with the current run and confirms the rename did
not alter build, signing or packaging behavior.

### Environment notes carried over

- The zig/0.15.2 tool package performed its expected `AccessDenied` retry
  while signing the generated Zig test runner; the upstream test target then
  completed with all 13 declarations passing.
- CI emitted a non-fatal pre-download warning (`No such file or directory:
  'curl'`) because device `curl` is not on the CI `PATH`; the pre-download
  fallback then correctly handed the source over to `conan create`, which
  downloaded `ncdu-2.9.2.tar.gz` itself.
- The device runner uses a read-only `/tmp`; temporary files must be redirected
  under `$HOME`. This is a device-environment property, recorded here only so
  future runs do not rediscover it.

### Historical 2026-08-17 runs

- Standard shadow CI stopped at L0k/R38 because the software-level
  `commands.json` did not exist yet; that file is now provided.
- An isolated `conan create` using the device-validated Zig cache exited 0 with
  all 13 upstream Zig tests passing.

## Reproducing the device run

Place the repository tree on a HarmonyOS device (or reuse an existing
checkout), then run:

```sh
CI_REPO_ROOT=<repo> \
  sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/n/ncdu/2.9.2
```

Shared dependencies do not need a pre-seeded cache: `conan create` resolves
`zig/0.15.2`, `ncurses/6.6` and `zstd/1.5.7.1` from `ohpcd` directly.

Signing relies on `binary-sign-tool` and `llvm-objcopy`, which the device
provides under `/data/service/hnp/bin` (already on the profile PATH) rather
than `/storage/Users/currentUser/usr/local/bin`.
