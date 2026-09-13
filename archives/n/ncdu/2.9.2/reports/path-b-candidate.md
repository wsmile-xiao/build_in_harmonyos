# ncdu 2.9.2 Path B candidate evidence

## Application

- Applicant: `@xuguowei`
- Team: Beidou Star
- Date: 2026-08-17 (package renamed to `ncdu` on 2026-09-11)
- Package: `ncdu/2.9.2`
- Issue: `https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2233`
- Branch: `feat/ncdu-2.9.2`
- Requested classification: Path A base adaptation plus Path B knowledge
  extension candidate

The final classification remains subject to maintainer review. This document
separates ncdu-specific knowledge from work contributed by its Zig tool
dependency.

## Package naming

Upstream names the project, the executable and the manual page `ncdu`; "ncdu 2"
is only the informal name of the 2.x branch on the project website. An earlier
round packaged 2.9.2 under the invented name `ncdu2` (merged as MR !6465) to
distinguish it from the C implementation of ncdu 1.x. This branch instead uses
`archives/n/ncdu/2.9.2` with `name = "ncdu"`, which matches the task branch
`feat/ncdu-2.9.2` required by CI gate L0n (R40). Recipe and test logic are
otherwise unchanged.

## Why this is a Path B candidate

ncdu 2.9.2 is a Zig command-line application with two native library
dependencies. A useful adaptation must do more than produce one executable:
it must connect Conan package roots to Zig's native dependency discovery,
preserve the upstream test target on HarmonyOS, and validate meaningful
non-interactive behavior for an application whose primary UI is terminal
based.

The candidate contribution is the combination of these three reusable
patterns:

1. Conan package roots are passed directly to Zig with one `--search-prefix`
   per dependency.
2. Release and upstream-test commands share the same dependency roots and
   isolated cache policy.
3. Device CI tests the installed application through deterministic JSON export
   instead of reducing coverage to `--version` or requiring a pseudo-terminal.

## Contribution 1: Conan-to-Zig dependency bridge

The recipe resolves the package folders for `ncurses/6.6` and `zstd/1.5.7.1`
through Conan's dependency model. It then invokes Zig with:

```text
zig build -j1 \
  --prefix <build>/zig-out \
  --search-prefix <ncurses-package> \
  --search-prefix <zstd-package> \
  -Doptimize=ReleaseFast -Dstrip=true
```

This avoids ambient compiler and linker variables, `pkg-config` state, and
host-specific installation prefixes. Missing package folders fail early with
an explicit configuration error instead of falling back to host libraries.

The same bridge is reusable for Zig projects whose `build.zig` uses
`addSearchPrefix`-compatible discovery for C libraries delivered by Conan.

## Contribution 2: upstream-test preservation

The recipe runs the upstream target rather than replacing it with an adapter
smoke test:

```text
zig build test -j1 \
  --search-prefix <ncurses-package> \
  --search-prefix <zstd-package>
```

Both commands use build-folder-local `ZIG_GLOBAL_CACHE_DIR` and
`ZIG_LOCAL_CACHE_DIR`. This keeps repeated jobs deterministic and prevents
state from a shared device cache from becoming an undeclared input.

Static source inventory found 13 Zig test declarations in seven source files.
The HarmonyOS build executed the upstream target successfully with all 13
declarations passing. No upstream tests were removed, rewritten, or reported
as passed without execution.

## Contribution 3: non-interactive semantic validation

ncdu is primarily an interactive terminal application, which makes a basic
TTY launch fragile and low-value in unattended CI. The `test_package` instead
uses the supported export workflow:

1. Assert exact `ncdu 2.9.2` version output.
2. Confirm help text advertises export mode.
3. Create a deterministic directory containing 17-byte and 31-byte files.
4. Scan it with `--ignore-config --apparent-size -0 -o <file>`.
5. Parse the JSON and verify format version, both names, and exact sizes.

This detects packaging, dynamic dependency, argument parsing, filesystem
traversal, output creation, and data-format regressions without depending on
terminal dimensions, key input, or timing.

## Failure evolution

1. W0 found `ncurses/6.6` and `zstd/1.5.7.1` on the `ohpcd` remote, but only
   Zig 0.16 packages. Upstream ncdu supports Zig 0.14 or 0.15.
2. Zig 0.15.2 was split into issue #2235 and PR #5562 in accordance with the
   one-library, one-issue, one-branch, one-PR rule.
3. A local Conan graph resolved after exporting the independent Zig recipe.
4. Standard shadow CI setup passed. L0 then stopped at R38 because a CLI
   package requires a software-level `commands.json`.
5. The isolated device build used the validated Zig package, built ncdu,
   executed all upstream tests, signed the final package executable, and ran
   the consumer test successfully.
6. `zig/0.15.2` was published to `ohpcd` and the software-level `commands.json`
   was added. On 2026-09-11 the standard shadow pipeline then passed end to
   end under the previous `ncdu2` package identity: G0/L0/L1/L2/L4/L5, KC and
   JC all pass, 13/13 upstream Zig tests pass, and the consumer test passes
   (exit 0).
7. The package name was corrected from `ncdu2` to `ncdu` so that the branch
   `feat/ncdu-2.9.2` satisfies CI gate L0n (R40). The standard device shadow
   CI was then re-run for `archives/n/ncdu/2.9.2` and passed again (exit 0,
   13/13), with L0j reporting a first publish.

## Device evidence

### Standard shadow CI, 2026-09-11 (PASS, current ncdu identity)

```text
RUN_DIR=/storage/Users/currentUser/ohpc-ci-shadow/runs/20260911T022038Z-c61fe5a0fe-15133
shadow input=repository snapshot of this branch's HEAD (ncdu 2.9.2)
exit=0
G0=pass  L0=pass (L0i/L0j/L0k/L0m all ok; L0j=first publish)
L1=pass  L2=pass  L4=pass  L5=pass   KC=pass   JC=pass
upstream Zig tests=13/13 pass
consumer test=pass (version, help, scan, JSON content and sizes)
Full package reference=ncdu/2.9.2#994731c20d2b252b373d6cf41d267438:
  b20ef63da03b6c8ae4b9b3674a4351bf36017117:
  92c626b497f9de8d910cb5314b2f5341
```

### Standard shadow CI, 2026-09-11 (PASS, previous ncdu2 identity)

```text
RUN_DIR=/storage/Users/currentUser/ohpc-ci-shadow/runs/20260911T015410Z-d6f07603ad-4795
shadow input=repository snapshot of origin/main 9b49d7903d + pending_ci manifest
exit=0
G0=pass  L0=pass (L0i/L0j/L0k/L0m all ok)  L1=pass  L2=pass  L4=pass  L5=pass
KC=pass  JC=pass
upstream Zig tests=13/13 pass
consumer test=pass (version, help, scan, JSON content and sizes)
Full package reference=ncdu2/2.9.2#abb700ad21db5710c40d7090ef315995:
  b20ef63da03b6c8ae4b9b3674a4351bf36017117:
  193b0eb19e577d9d7999a2527500e1a0
```

### Standard shadow CI, 2026-08-17 (historical, blocked at L0k/R38)

```text
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-shadow-ci-r1-20260817-093824-48508
shadow input=caaded2b0ff5934696d96bfb64d7f687ac94c9cd
setup=pass
L0=fail (commands_json_r38)
L1/L2/L4/L5=skipped by gate ordering
```

### Isolated Conan create, 2026-08-17

```text
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-conan-create-r1-20260817-094126-49916
exit=0
upstream Zig tests=13/13 pass
consumer test=pass (version, help, scan, JSON content and sizes)
package ID=b20ef63da03b6c8ae4b9b3674a4351bf36017117
package revision=7f1b56658afbf73f1ebfdc0ceadb0ab6
```

## Boundary with Zig PR #5562

The following capabilities are prerequisites reused from Zig and are not
claimed as new ncdu knowledge:

- signed PIE launchers for scripts on hmdfs;
- automatic signing and retry for Zig-generated ELF files;
- Zig 0.15.2 distribution and standard-library compatibility handling.

ncdu's final executable is signed as a packaging requirement, but generic
HarmonyOS ELF signing is likewise not counted as this candidate's innovation.

## Known limits

- Interactive ncurses navigation is not automated; deterministic export mode
  covers the scanner and output semantics without a TTY.
- CI emits a non-fatal pre-download warning because device `curl` is not on the
  CI `PATH`; Conan downloads the source itself, so source binding is unaffected.
- The rename from `ncdu2` to `ncdu` invalidates the earlier device run as
  evidence for the new package reference; a re-run is pending.

## Verification status

The standard pipeline passed under the current `ncdu` identity:

```text
run_id=20260911T022038Z-c61fe5a0fe-15133   exit=0
G0/L0/L1/L2/L4/L5=pass   KC=pass   JC=pass
upstream Zig tests: all 13 passed
test_package: version, help, scan, and JSON export passed
package reference: ncdu/2.9.2#994731c20d2b252b373d6cf41d267438:
                   b20ef63da03b6c8ae4b9b3674a4351bf36017117:
                   92c626b497f9de8d910cb5314b2f5341
```

The same pipeline had already passed under the previous `ncdu2` identity
(run-id `20260911T015410Z-d6f07603ad-4795`, exit 0), which confirms the rename
did not change build, signing or packaging behavior. To reproduce on a device
with the repository tree available:

```sh
CI_REPO_ROOT=<repo> sh "$HOME/bin/run-ohos-shadow-ci.sh" archives/n/ncdu/2.9.2
```
