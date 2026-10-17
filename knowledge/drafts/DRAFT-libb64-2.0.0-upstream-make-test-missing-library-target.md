# DRAFT: libb64 2.0.0 — Upstream `make test` Missing Library Target (OHOS Portability / Test Workflow)

> Status: Draft | Updated: 2026-08-31
> Source: libb64 2.0.0 R01/R02 适配（build_in_harmonyos，archives/l/libb64/2.0.0，feat/libb64-2.0.0）
> Executor: pc3-46 | task_id: libb64-2.0.0-r03-path-b-knowledge-draft-pc3-46-20260831T030000Z
> Official source: https://github.com/stefantalpalaru/libb64 tag v2.0.0 (commit 293fb02), SHA-256 28c43c47674409fc50e7145d4c2d26dc1f3d200889c41205e7812c2b67f26382

## Summary

libb64 2.0.0's upstream `examples/Makefile` exposes a `make test` target
(`test: test-c-example1 test-c-example2`) but the recipe/`src/Makefile` does not
declare a `libb64.a` build target that `examples/Makefile` depends on. In a clean
source tree on OHOS this upstream entry exits 2 (`No rule to make target
'libb64.a'`). This is a reusable testing-and-portability workflow lesson: on
OHOS, a failed upstream test entry must be preserved as an upstream-entry result
and replaced by an equivalent, API-calling test with an explicit test ledger.

## Error Signature

```
make: *** No rule to make target 'libb64.a', needed by 'c-example1'.  Stop.
```

Entry: `examples/Makefile` target `test` (and its dependencies
`test-c-example1`, `test-c-example2`), cwd = unpacked `libb64-2.0.0/examples`.
Exit code 2 (make "no rule" failure).

## Trigger

`libb64/2.0.0` first-round local adaptation (R02). The upstream `test` target
was attempted verbatim with `make test` from `examples/`. `examples/Makefile`
contains `c-example1 c-example2: libb64.a` (implicit prerequisite on the
archive), but the build graph provides no rule to produce `libb64.a` (the
archive is normally built by `src/Makefile` into `src/`, which is not a
prerequisite of the examples target). Therefore in a clean tree the target fails
with exit 2 before any example binary is built.

## Root Cause

`examples/Makefile` assumes a prebuilt `libb64.a` (from `src/`, via the implicit
`vpath %.a ../src` + implicit rule chain), but the `test` target itself does not
drive that build and there is no `all`-level ordering that guarantees `src` is
built first when invoking `make test` directly. On OHOS (and any clean-source
workflow) this yields the missing-target exit 2. It is an upstream build-graph
assumption, not a bug in the library sources and not an OHOS-specific compile
error.

## Solution

Preserve the failed upstream entry as an upstream-entry result (do not hide or
"fix" it by patching upstream). Then provide an equivalent API-calling test built
with the OHOS clang toolchain and record an explicit test ledger:

1. **Preserve upstream entry**: keep `make test` as the recorded upstream entry
   with its real exit code 2 and first stdout/stderr, so the ledger reflects the
   true upstream behavior in a clean tree.
2. **Equivalent API test**: compile `src/cencode.c` + `src/cdecode.c` with OHOS
   clang (`/data/service/hnp/bin/clang`), archive into `libb64.a`, then either
   build the two official examples or an equivalent test that actually calls the
   public C API:
   - `base64_encode_block` / `base64_encode_blockend` → expected
     `SGVsbG8sIGxpYmI2NCE=`
   - `base64_decode_block` (padded one-shot and multi-call streaming) → exact
     plaintext length and byte-exact match
   - helper `base64_encode_length` / `base64_decode_maxlength`
3. **Ledger**: record for each entry command, cwd, exit code, absolute log path,
   and SHA-256 of the log, separately from the upstream entry.

The test_package `test_b64.c` (6 assertions) and the OHOS-specific
`test_harmonyos.c` implement the equivalent API tests; upstream examples
`c-example1.c` / `c-example2.c` are also compiled and run as additional evidence.

## Validation (R02 evidence, traceable)

| item | value |
|------|-------|
| `make test` upstream entry | exit 2, `No rule to make target 'libb64.a'` (log `upstream_tests`) |
| OHOS clang compile `src/cencode.c` + `src/cdecode.c` → `libb64.a` | exit 0 |
| `c-example1` run | exit 0 (strcmp round-trip assertion passed) |
| `c-example2` encode/decode + `diff -q` | exit 0, DIFF_MATCH |
| `test_b64` (test_package) | 6/6 assertions passed |
| `test_harmonyos` (OHOS-specific) | PASSED; aarch64 ELF, OHOS macro defined, padded/streaming decode byte-exact |
| `conan create` (clean build + test_package) | exit 0, package `libb64/2.0.0@ohpcd/stable` |

## Applicability Boundaries

- Applies to any upstream Makefile whose test target assumes a prebuilt library
  archive not produced by the same target invocation.
- OHOS/OpenHarmony portability-and-testing workflow: failed upstream entries are
  preserved as entries, never silently deleted; an equivalent API-calling test
  plus ledger replaces the broken entry for local verification.
- Does not modify upstream sources or assertions; does not patch
  `examples/Makefile`.
- Not an upstream-assertion change and not a library compile fix.

## Deduplication

Searched `knowledge/**` (graph/index.tsv + graph/*.kv + doc/*.md + drafts/*) for
`libb64|base64`, `make test` + missing library target, and test-portability
wording. Only `E270-draft-2301` matched the substring `base64`, but its topic is
ITK 5.4.6 offline test-input closure (ExternalData/CID objects + binary patch
transport); `base64` there is only a transport encoding, not a libb64 problem.
No existing entry shares this error signature, root cause, or solution. This
pair is a distinct, new draft (intentional extension of the testing-workflow
knowledge area).
