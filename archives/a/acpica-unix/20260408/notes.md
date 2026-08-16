# acpica-unix 20260408 HarmonyOS pre-adaptation notes

Issue: 2207

## Scope and source

- Worktree: `D:\harmonyos\worktrees\acpica-unix`
- Branch: `feat/acpica-unix-20260408-2207`
- Official source: `acpica-unix-20260408.tar.gz` from the ACPICA 20260408 release
- SHA-256: `e66ceb26d6d514ce164fe22f5a4f7ca165cc38349d7a97f41a21f19b364647a2`
- Source analysis used official tag `20260408` at commit
  `232ff3f8ae1a4da11c709f61d9154482cfe8e6df` via a GitCode mirror because
  direct GitHub downloads were unavailable on the Windows host.

## W0 dependency check

Upstream requires `make`, a C compiler, `bison`/`yacc`, `flex`/`lex`, and `m4`.
The recipe declares the non-base build tools as Conan tool requirements:

- `bison/3.8.2`
- `flex/2.6.4`
- `m4/1.4.19`

Repository evidence shows version-level recipes for all three. Their manifests
are `built`, not `published`, and the local `m4/1.4.19` manifest contains an
older failed remote check. Because the Windows host has no Conan installation,
W0 was completed with anonymous read-only queries against the Conan v2 API at
the repository-configured CNB remote. All three recipes are currently present:

- `bison/3.8.2`: revision `27704878ab972a7b7a0a560e22360cbb`
- `flex/2.6.4`: revision `dae8938545a70afe5596b280fc4ad124`
- `m4/1.4.19`: revision `9a84a566238ea69b63e725d646354933`

W0 therefore passes. Reconfirm from the isolated OHOS job before building:

```sh
conan download "bison/3.8.2" -r=ohpcd --only-recipe
conan download "flex/2.6.4" -r=ohpcd --only-recipe
conan download "m4/1.4.19" -r=ohpcd --only-recipe
```

If a later Conan client check fails, finish and publish that dependency in its
own issue, branch, and PR before resuming issue 2207.

## Build-system analysis

ACPICA uses a top-level Makefile that dispatches to `generate/unix`. The Unix
configuration builds eight commands:

`acpibin`, `acpidump`, `acpiexamples`, `acpiexec`, `acpihelp`, `acpisrc`,
`acpixtract`, and `iasl`.

The upstream host detection does not know OHOS, so the recipe explicitly sets
`ACPI_HOST=_LINUX`. The compiler comes from Conan's
`tools.build:compiler_executables` configuration. `NOWERROR=TRUE` avoids
turning compiler-version warning differences into porting failures, and
`NOFORTIFY=TRUE` avoids a conflicting `_FORTIFY_SOURCE` definition. The build
is serialized with `-j1` for the shared parser-generation tree.

There are no third-party runtime libraries. `acpiexec` uses the platform
pthread and realtime interfaces, and `acpidump` uses host ACPI/device access;
those two areas are the highest-probability OHOS compile/runtime risks.

## Test strategy and pruning

The full ACPICA and ASL test suites are shipped separately as
`acpitests-unix-20260408.tar.gz`; they are not contained in the selected source
archive and therefore are not silently claimed as passing. The selected source
does contain the official table-template test flow in `tests/templates`.

The recipe exercises a deterministic subset during build by generating and
compiling the DSDT template. The consumer `test_package` performs a substantive
round trip with the packaged `iasl`: version check, ASL-to-AML compilation,
AML-to-ASL disassembly, method-content assertion, and recompilation. The full
separate test-suite integration remains follow-up work after dependencies and
the first OHOS build are available.

## Current verification

- Official release URL and SHA-256 cross-checked against the upstream release.
- Official tag and commit inspected.
- Conan recipe and test recipe prepared.
- Python AST parsing, shell syntax, text/whitespace, and SHA field checks pass.
  YAML parser validation remains unavailable because neither local Python
  environment contains a YAML parser.
- No local build was possible: this host has no Conan, WSL distribution,
  `make`, compiler, `bison`, `flex`, or `m4`.
- Shadow CI passed on the OHOS aarch64 device for commit
  `b6007b3495b58bc67e1a791cf2c4b8dc10666132` in isolated run
  `codex-acpica-unix-issue-2207-shadow-r1-20260815-215836-9865`.
- CI summary: total 1, success 1, failed 0. L0, L1, L2, L4, and L5 passed.
  The L1e destructive negative test also passed, confirming that the consumer
  test genuinely depends on the packaged tools.
- The package contains all eight expected executables. `file` identifies each
  as an ARM aarch64 PIE using `/lib/ld-musl-aarch64.so.1`.
- The packaged `iasl` completed the substantive test flow on-device: version
  check, ASL compilation, AML disassembly, method-content assertion, and
  round-trip recompilation.
- Generic L2 probing reported non-blocking warnings for tools that do not
  accept the runner's standard `--version`/`--help` forms (`acpibin`,
  `acpihelp`, `acpisrc`, and `iasl`). This is covered by the successful
  package-specific `iasl` test and by successful L2 probes for `acpidump`,
  `acpiexamples`, `acpiexec`, and `acpixtract`.
- The generated `ci-metadata.json` records an empty source URL because shadow
  CI temporarily rewrites a GitHub URL into a YAML list for mirror fallback,
  while its metadata extractor only reads an inline quoted scalar. The source
  archive was still downloaded and verified against the declared SHA-256.
  This is a generic CI observability issue and does not require a package
  workaround.

## Submission metadata

The task owner authorized the software-level
`archives/a/acpica-unix/commands.json` required by CI L0k. It declares this
package as a tool and keeps `binary: false` until the OHOS package is built and
published.

## Final-head OHOS/shadow CI command

The validation-result documentation changes the commit SHA, so rerun the same
single-package command against the final committed HEAD:

```sh
CI_PACKAGES="archives/a/acpica-unix/20260408" zsh ci/conan/build_and_test.sh
```

The isolated device job and heavy runner invocation are:

```sh
. "$HOME/ohos-users/codex/acpica-unix-2207-b6007b3495/env.sh"
sh "$HOME/bin/ohos-test-runner.sh" \
  --user codex --lib acpica-unix --task issue-2207-shadow-final \
  --mode heavy --try-lock --workdir "$CI_REPO_ROOT" -- \
  zsh "$HOME/ohos-users/codex/acpica-unix-2207-b6007b3495/work/run-acpica-shadow.zsh"
```

Queue metadata:

```text
library: acpica-unix
branch: feat/acpica-unix-20260408-2207
issue: 2207
package: archives/a/acpica-unix/20260408
resource: CPU / IO
observed duration: 3 minutes 9 seconds for the initial isolated build
heavy task: yes
```

## Path B official-test expansion

The official `acpitests-unix-20260408.tar.gz` asset is now a separately pinned
test source with SHA-256
`e7bc47d40c1836dc65af8521d2f900850f3f0fdac7ea780ba59ac644d8625f5c`.
It contains 1,291 `.asl` files. The recipe dynamically inventories the asset
and the selected `functional/constant` directory (4 `.asl` files), then runs
only the `constant` collection in `n64` mode with the published `bash/5.3`
tool requirement. This is a named subset, not a full-suite claim.

The original upstream runner produced a reproducible false green in
`codex-acpica-unix-issue-2207-aslts-baseline-20260815-223846-37405`: copying
`iasl`, `acpiexec`, and `acpibin` to hard-coded `/tmp` failed because the mount
is read-only, the runner printed `iasl compiler not found`, and still returned
0 because the error path used bare `exit`.

Further fail-fast iterations exposed two additional false-green paths:

- transitive scripts used a fixed `/bin/bash` shebang even though the top-level
  runner was started with Conan Bash;
- Toybox rejected GNU `xargs -I`, while the runner returned 0 and generated a
  Summary with empty PASS, FAIL, and Tests fields.

The test-asset-only portability patch now honors a writable `TMPDIR`, uses
explicit nonzero error propagation, dispatches transitive scripts through the
active Conan Bash, executes the selected case sequentially, and allows the
unrelated template/history phases to be skipped explicitly. The production
ACPICA source and test assertions are unchanged.

Final targeted run
`codex-acpica-unix-issue-2207-aslts-constant-n64-v4-20260815-232510-57982`
passed under the global heavy-task lock with:

```text
PASS=1
FAIL=0
Tests=1
Test Cases=1 (of 48)
Test Collections=1 (of 8), functional
constant.aml=18522 bytes
```

The recipe parses the latest 64-bit nopt Summary and requires numeric non-empty
counts (`PASS > 0`, `FAIL == 0`, `Tests > 0`) plus the AML artifact before
accepting the upstream result.

## B-class shadow CI result

Full shadow CI first exposed that the ASLTS Makefile used `install -d` for pure
directory creation. OHOS rejected that executable inside the Conan build
environment; the recipe's positive-artifact gate correctly failed because no
`constant.aml` existed. The test-only patch now uses `mkdir -p` for that rule.

Commit `8017c26133dbb72a1ac9e4fc2edb01b006c8c28a` passed the complete single-package
shadow CI in run
`codex-acpica-unix-issue-2207-shadow-bclass-r2-20260815-234914-11351`:

```text
ASLTS_INVENTORY total_asl=1291 selected_case=constant selected_asl=4 selected_mode=n64
ASLTS_SUBSET_PASS total_asl=1291 selected_case=constant selected_asl=4 selected_mode=n64 generated_aml=1 pass=1 fail=0 tests=1
L0_RESULT=pass
L1_RESULT=pass
L1e=pass (destructive negative test)
L2_RESULT=pass
L4_RESULT=pass
L5_RESULT=pass
Total=1 Success=1 Failed=0
```

The run acquired the global heavy-task lock without waiting, finished in 3
minutes 22 seconds, and produced no runner stderr. L2 retains the known
non-blocking standard version/help warnings for four ACPICA tools; package-
specific `iasl` coverage and the consumer round trip both passed.

The validation-result update changes HEAD, so the final committed HEAD must be
rerun with the same single-package command before PR submission.
