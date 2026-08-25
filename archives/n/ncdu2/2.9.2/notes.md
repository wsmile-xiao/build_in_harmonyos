# ncdu2 2.9.2 HarmonyOS adaptation notes

## Scope and source

- Issue: `https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2233`
- Adaptation path: Path A (base adaptation) plus Path B (knowledge extension
  candidate).
- Upstream project: `ncdu` 2.x, packaged as `ncdu2` to distinguish the Zig rewrite.
- Official release: `https://dev.yorhel.nl/download/ncdu-2.9.2.tar.gz`
- Verified SHA-256: `e91135281cb66569f2ca4c0bac277246991e7e52524c0ca8cba3de5c8e81cec9`.
- Build system: Zig `build.zig`; the bundled Makefile is only a convenience wrapper.

## Dependency analysis

Required runtime/link dependencies:

- `ncurses/6.6`: published on the `ohpcd` Conan remote.
- `zstd/1.5.7.1`: published on the `ohpcd` Conan remote.

Required build dependency:

- Upstream explicitly supports Zig 0.14 or 0.15.
- The `ohpcd` remote currently publishes only `zig/0.16.0` and
  `zig/0.16.0.1`.
- Issue #2235 now contains a separate `zig/0.15.2` recipe on branch
  `feat/zig-0.15.2-2235`, submitted independently as PR #5562. Its isolated
  HarmonyOS aarch64 `conan create` completed with exit 0, including the Zig
  `test_package`; publication remains pending.
- The recipe therefore declares `tool_requires("zig/0.15.2")` and remains
  blocked until that compiler package is published from its own issue, branch,
  and PR.
- Zig is a real build requirement, but its issue classification and knowledge
  contribution remain independent from this ncdu2 Path B application.

The dependency is not vendored or downloaded from this recipe. Doing so would
mix the missing Zig adaptation into the ncdu2 PR and violate the dependency
split rule.

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

A local Conan graph resolves `ncurses/6.6`, `zstd/1.5.7.1`, and the locally
exported `zig/0.15.2` recipe. The same dependency set was subsequently built
and tested on the HarmonyOS aarch64 device as recorded below.

## Known gate conflict

`ncdu2` is a command-line application, so repository gate L0k requires a
software-level `archives/n/ncdu2/commands.json`. This round is explicitly
restricted to `archives/n/ncdu2/2.9.2/`, so that file is not added. The recipe
keeps its truthful `package_type = "application"` and `bindirs = ["bin"]`;
there is no attempt to bypass the gate. Standard shadow CI confirmed this is
the only failing L0 gate after dependency availability was reported as an R36
warning.

## Path B knowledge-extension candidate

The ncdu2-specific reusable contribution is intentionally separate from the
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

## Real-device verification

On 2026-08-17, both jobs ran through the global single-package runner lock.

- Standard shadow CI run:
  `/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-shadow-ci-r1-20260817-093824-48508`
- The shadow input was commit `caaded2b0ff5934696d96bfb64d7f687ac94c9cd`.
  Setup passed; L0 failed at `commands_json_r38`; L1/L2/L4/L5 were skipped.
- Isolated `conan create` run using the device-validated Zig cache:
  `/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-conan-create-r1-20260817-094126-49916`
- The job exited 0. The signing wrapper recovered from the expected initial
  generated-runner `AccessDenied`, and all 13 upstream Zig tests passed.
- `ncdu` was signed successfully. Package ID:
  `b20ef63da03b6c8ae4b9b3674a4351bf36017117`; package revision:
  `7f1b56658afbf73f1ebfdc0ceadb0ab6`.
- The installed package passed version/help checks, deterministic directory
  scanning, and JSON export content/size assertions.

## Next validation

After `zig/0.15.2` is independently published and the L0k metadata scope is
resolved, rerun the standard pipeline without the local dependency cache:

```sh
conan download "zig/0.15.2" -r=ohpcd --only-recipe
conan download "ncurses/6.6" -r=ohpcd --only-recipe
conan download "zstd/1.5.7.1" -r=ohpcd --only-recipe
CI_PACKAGES="archives/n/ncdu2/2.9.2" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/n/ncdu2/2.9.2
```
