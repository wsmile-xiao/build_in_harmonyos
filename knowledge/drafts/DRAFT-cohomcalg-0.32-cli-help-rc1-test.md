# Draft: CLI --help may legitimately exit 1 — smoke test must check banner, not rc

> Source event: `cohomcalg/0.32` test_package first failure on 2026-09-08.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.

## Problem

`cohomcalg` 0.32 prints its help banner for `--help` but returns exit code 1
(`ParseCmdLineArguments()` returns false; `main()` does `return 1;`). A
test_package smoke test written as

```bash
"$BIN" --help > help.out 2>&1 || { echo "❌ --help failed"; exit 1; }
```

fails spuriously:

```text
[test] cohomcalg --help
❌ --help failed
ERROR: Error in test() method, line 20
ConanException: Error 1 while executing
```

The banner is present in the output; only rc is 1. This is upstream behaviour
for legacy CLIs, not a defect.

## Fix

Tolerate the help exit code and assert on output content; keep the real
correctness gate on an actual computation:

```bash
"$BIN" --help > help.out 2>&1 || true
grep -Fq "cohomCalg v0.32" help.out && echo "✅ --help banner OK (v0.32)"
# primary gate: run a sample input and assert the mathematical result
"$BIN" --integrated --nomonomfile "$TMPD/dP1.in" > dP1.out 2>&1
grep -Fq "{{0,1,0},{{1,1*u3*u4}}}" dP1.out
grep -Fq "Program run successfully completed" dP1.out
```

## Verification

- `conan create` (ohos-aarch64) with the fixed test.sh → PASS (test_package green)
- 6/7 upstream samples pass; OHOS test 5/5

## Applicability / Counter-examples

- Any CLI whose `--help` returns non-zero by design.
- Counter-example: `--version`/`--help` returning 0 (E503 jshn precedent —
  there a patch made them return 0); tools with mandatory-config fail-closed
  semantics (E357) need an allowlist approach instead.

## Relations

- similar_to: [E503, E357] — smoke-test help handling and informational-option allowlists
- Not caused by / prerequisite of existing entries; no conflict.

## Records

- success_count: 1, fail_count: 1, confidence: 0.8
- contributor: pc1-34