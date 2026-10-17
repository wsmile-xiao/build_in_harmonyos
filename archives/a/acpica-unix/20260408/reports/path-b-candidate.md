# acpica-unix 20260408 Path B candidate report

Issue: 2207
Date: 2026-08-15

## Candidate conclusion

This adaptation is a B-class knowledge expansion candidate. It adds an
acpica-derived draft that addresses a reusable failure class: a legacy Bash
upstream harness can encounter a read-only temporary directory, a missing
system Bash, or an unsupported utility flag and still return zero without
executing a test. The proposed rule requires fail-fast phase propagation and
a non-empty structured result plus a positive artifact.

Draft files:

- `knowledge/drafts/E327-draft-acpica-aslts-false-green.kv`
- `knowledge/drafts/E327-draft-acpica-aslts-false-green.md`

## Official assets and inventory

| Asset | SHA-256 |
|---|---|
| `acpica-unix-20260408.tar.gz` | `e66ceb26d6d514ce164fe22f5a4f7ca165cc38349d7a97f41a21f19b364647a2` |
| `acpitests-unix-20260408.tar.gz` | `e7bc47d40c1836dc65af8521d2f900850f3f0fdac7ea780ba59ac644d8625f5c` |

The test asset contains 1,291 `.asl` files. The recipe computes this inventory
at build time and also computes the selected `functional/constant` inventory
(4 `.asl` files). It runs only `constant` in `n64` mode and does not claim the
other collections, modes, or the full data-table template phase.

## Before/after evidence

| Run | Exit | Audited result |
|---|---:|---|
| `codex-acpica-unix-issue-2207-aslts-baseline-20260815-223846-37405` | 0 | False green: three `/tmp` copies failed and `iasl compiler not found`; no test ran |
| `codex-acpica-unix-issue-2207-aslts-patched-20260815-225949-48211` | 1 | Fail-fast exposed the incorrect caller working directory |
| `codex-acpica-unix-issue-2207-aslts-constant-n64-v2-20260815-231514-53840` | 0 | Still false green: Toybox rejected `xargs -I`; Summary counts were empty |
| `codex-acpica-unix-issue-2207-aslts-constant-n64-v4-20260815-232510-57982` | 0 | Real pass: Summary PASS 1 / FAIL 0 / Tests 1; one 18,522-byte `constant.aml`; START and SUCCESS markers |
| `codex-acpica-unix-issue-2207-shadow-bclass-20260815-233817-4051` | 1 | Full recipe exposed policy-blocked `install -d`; no AML caused the positive-artifact gate to fail |

All device runs used the global heavy-task lock and the issue-specific isolated
workspace. The final targeted run acquired the lock with zero seconds wait.

## Minimal portability patch

`patches/0001-aslts-ohos-portable-runner.patch` changes only the separately
released upstream test harness:

1. honors and validates `TMPDIR` instead of hard-coding `/tmp`;
2. returns nonzero from setup, copy, template, compile, and execution failures;
3. invokes `Do` and `asltsrun` through the active Conan Bash;
4. offers explicit template and historical-result-comparison switches for an
   evidence-bounded isolated subset;
5. replaces GNU-specific `xargs -I/-P` dispatch with a sequential selected-case
   loop so test status remains in the calling shell;
6. uses `mkdir -p` for pure result-directory creation instead of an `install`
   executable rejected by the OHOS policy inside the Conan build environment.

ACPICA production source and assertions are unchanged. The patch SHA-256 is
`1019cfd24ecbe6e979e615d2d6e7ac954b6b426021b4c67853ec8861894507fd`.

## Acceptance gate

The Conan recipe does not trust process exit zero alone. It requires:

- a complete official test asset and non-empty dynamic inventories;
- `constant.aml` below the current ASLTS version/mode output;
- a latest Summary containing numeric counts for 64-bit nopt mode;
- `PASS > 0`, `FAIL == 0`, and `Tests > 0`.

The recipe emits `ASLTS_SUBSET_PASS` only after all gates pass. Existing DSDT
template generation and the packaged `iasl` consumer round trip remain
independent coverage.

## Relationship to existing knowledge

- E002 explains writable `TMPDIR`; it does not prevent a bare-exit false green.
- E201 explains missing `/bin/bash`; it does not cover transitive interpreter
  dispatch from a Conan tool dependency.
- E253 establishes truthful upstream-suite reporting; the new draft adds the
  concrete empty-Summary and positive-artifact gate.

Full single-package shadow CI passed at commit `8017c26133` in
`codex-acpica-unix-issue-2207-shadow-bclass-r2-20260815-234914-11351`.
The run emitted the expected 1,291/4 inventory and non-empty pass marker; L0,
L1, L2, L4, L5, and the L1e destructive negative test passed. The metadata-only
commit that records this result still requires the standard final-HEAD rerun.
