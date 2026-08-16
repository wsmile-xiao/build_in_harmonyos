# Local and device validation

Date: 2026-08-13

## Static checks

- Source archive SHA-256 matches
  `668be900964b2e42e55c3f921e2d2a1d54ca618583a6681ccaefc01fbf2aa793`.
- Both Conan Python files pass Python 3.12 compilation and AST parsing.
- The portability patch applies cleanly to the verified v0.11.2 source.
- Patch SHA-256 is
  `d11850a401d0b0d6df83e8dd898de661ee3ec19e1d68181d3a531cb81ea9066a`.
- All branch changes are under `archives/a/acf-openssh/0.11.2/`.
- YAML files parse on the target device; `test_layout.sh` passes target `sh -n`.
- `git diff --check` reports no whitespace errors.

## Shadow CI investigation

All runs used the single-package heavy runner, a fresh run directory, a fresh
`CONAN_HOME`, the OHOS aarch64 profile, and a temporary source overlay of the
separate luaposix PR. The acf branch itself contains no dependency files.

1. Run `97f27e7dbb08-20260813T065935Z-run-12622` built the full dependency
   graph and acf package, then failed layout validation. The package contained
   only nine regular resources; the three upstream dangling links were absent.
2. Run `97f27e7dbb08-20260813T070435Z-run-15767` attempted to reconstruct the
   links explicitly and failed in `package()` with
   `PermissionError: [Errno 13] Permission denied` from `os.symlink`.
3. Run `97f27e7dbb08-20260813T071218Z-run-20217` validated the no-link fix from
   the worktree: all 48 checks passed.
4. Final run `b4c79d112872-20260813T072224Z-run-25623` repeated the complete
   build from a fresh cache using the exact committed acf source snapshot.

## Final result

```text
acf_commit=b4c79d1128721ac86656048d1d8d7ce052b0769f
dependency_commit=754dc4142f7ef00331cd0614c1cfe7cc9e104c81
setup_rc=0
build_rc=0
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=warn: no artifacts found
ACF_OPENSSH_TEST: 32 checks passed
layout checks: 16 passed
total checks: 48 passed
input verification sha256: 9c464c9649089355a8b158815a8f4884d854f9127fbe24cc16e0d2ea5537ef37
build log sha256: 247ed439056b1946e1ebd8b4595f44bd4923920e677632f4a7df7f414485a32c
```

L2 and L5 are expected for this pure ACF resource package: it intentionally
contains neither executables nor a `lib/` directory.

## Formal CI infrastructure failures

Two formal CI attempts failed before the repository or recipe could be
executed:

| CI | Worker | First failed step | Raw failure |
|----|--------|-------------------|-------------|
| #24119 | OpenHarmonyPCDeveloper-CI-026 | `worker-prep` | SSH bridge `Connection refused (111)` |
| #24130 | OpenHarmonyPCDeveloper-CI-006 | `worker-prep` | SSH bridge `Connection refused (111)` |

Both runs have the same ordering and failure boundary:

1. The first worker command, `mkdir -p ...`, was not started because the SSH
   bridge could not connect to the worker.
2. The following checkout probe, `git -c safe.directory=* --version`, failed
   through the same bridge before Git could run.
3. Cleanup also could not connect to the worker.
4. There is no source request, Conan dependency resolution, recipe execution,
   compilation, or test output in either log.

The automated diagnosis labels these runs as source download timeouts, but
that label conflicts with the raw logs: the failure precedes repository
checkout and no source URL was accessed. It is therefore not actionable in
`conandata.yml` or `conanfile.py`. Replacing the SHA-256-verified official
source URL would not restore the unavailable SSH bridge.

Correct follow-up is to retry on an available worker and classify the next
result separately:

- another pre-checkout SSH refusal is a CI infrastructure failure;
- a missing `luaposix/36.3.1.1` during Conan graph resolution is the documented
  dependency publication gate from PR #5204;
- only an error after recipe execution starts is an acf-openssh implementation
  failure.

The candidate device result above remains the only run that executed this
recipe and its 48 checks; it passed. Formal CI must still be rerun after the
worker bridge is available and, for a release-complete result, after PR #5204
is merged and the dependency is published.

## Formal CI G0 correction

Formal CI #24148 on Worker OpenHarmonyPCDeveloper-CI-011 passed worker
preparation, checkout, and Conan setup. Its first failure was the repository
knowledge integrity gate, before package dependency resolution:

```text
G0a: knowledge/graph/draft/ directory contains 1 draft
Drafts are allowed only in knowledge/drafts/
```

The directly related E327 pair is stored at:

- `knowledge/drafts/E327-draft-acf-openssh.kv`
- `knowledge/drafts/E327-draft-acf-openssh.md`

After the move, the forbidden `knowledge/graph/draft/` directory contains zero
`.kv` files. The repository `ci/scripts/knowledge_check.sh` completed KC1-KC5
with `KC_RESULT=pass` and `KC_ERRORS=0`. This fixes the actual #24148 failure;
the next formal run can proceed to package dependency resolution.

## Dependency release cleared

PR #5204 was merged at `1e58af5de4c938790b33de891fe9521e2163d249`.
On 2026-08-15 the official anonymous `ohpcd` Conan v2 endpoint returned
HTTP 200 for `luaposix/36.3.1.1`, with recipe revision
`8bf168040d86e8aabd8feca6afc33a5d` published at
`2026-08-15T10:08:35Z`. W0 is therefore closed.

The remaining validation is to rerun acf-openssh itself without the temporary
dependency overlay:

```sh
conan download "luaposix/36.3.1.1" -r=ohpcd --only-recipe
CI_PACKAGES="archives/a/acf-openssh/0.11.2" zsh ci/conan/build_and_test.sh
```
