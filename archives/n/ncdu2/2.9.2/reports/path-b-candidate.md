# ncdu2 2.9.2 Path B candidate evidence

## Application

- Applicant: `@xuguowei`
- Team: Beidou Star
- Date: 2026-08-17
- Package: `ncdu2/2.9.2`
- Issue: `https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/2233`
- Branch: `feat/ncdu2-2.9.2-2233`
- Requested classification: Path A base adaptation plus Path B knowledge
  extension candidate

The final classification remains subject to maintainer review. This document
separates ncdu2-specific knowledge from work contributed by its Zig tool
dependency.

## Why this is a Path B candidate

ncdu2 2.9.2 is a Zig command-line application with two native library
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
The isolated HarmonyOS build executed the upstream target successfully with
all 13 declarations passing. No upstream tests were removed, rewritten, or
reported as passed without execution.

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
   Zig 0.16 packages. Upstream ncdu2 supports Zig 0.14 or 0.15.
2. Zig 0.15.2 was split into issue #2235 and PR #5562 in accordance with the
   one-library, one-issue, one-branch, one-PR rule.
3. A local Conan graph resolved after exporting the independent Zig recipe.
4. Standard shadow CI setup passed. L0 then stopped at R38 because a CLI
   package requires software-level `archives/n/ncdu2/commands.json`.
5. The isolated device build used the validated Zig package, built ncdu,
   executed all upstream tests, signed the final package executable, and ran
   the consumer test successfully.

The R38 file is outside the permitted
`archives/n/ncdu2/2.9.2/` scope and is therefore not added by this PR.

## Device evidence

### Standard shadow CI

```text
RUN_DIR=/storage/Users/currentUser/ohos-test-runs/codex-ncdu2-2.9.2-2233-shadow-ci-r1-20260817-093824-48508
shadow input=caaded2b0ff5934696d96bfb64d7f687ac94c9cd
setup=pass
L0=fail (commands_json_r38)
L1/L2/L4/L5=skipped by gate ordering
```

### Isolated Conan create

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
claimed as new ncdu2 knowledge:

- signed PIE launchers for scripts on hmdfs;
- automatic signing and retry for Zig-generated ELF files;
- Zig 0.15.2 distribution and standard-library compatibility handling.

ncdu2's final executable is signed as a packaging requirement, but generic
HarmonyOS ELF signing is likewise not counted as this candidate's innovation.

## Known limits

- `zig/0.15.2` has passed isolated device validation but PR #5562 is not yet
  merged or published to `ohpcd`.
- Standard shadow CI cannot proceed beyond R38 until the software-level command
  metadata scope is resolved by maintainers or a separately authorized change.
- Interactive ncurses navigation is not automated; deterministic export mode
  covers the scanner and output semantics without a TTY.
- The successful isolated build does not replace a clean standard pipeline run
  after dependency publication.

## Next verification

After Zig 0.15.2 is merged and published:

```sh
conan download "zig/0.15.2" -r=ohpcd --only-recipe
conan download "ncurses/6.6" -r=ohpcd --only-recipe
conan download "zstd/1.5.7.1" -r=ohpcd --only-recipe
CI_PACKAGES="archives/n/ncdu2/2.9.2" zsh ci/conan/build_and_test.sh
/path/to/run-ohos-shadow-ci.sh archives/n/ncdu2/2.9.2
```
