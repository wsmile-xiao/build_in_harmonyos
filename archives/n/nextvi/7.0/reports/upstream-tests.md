# nextvi 7.0 upstream test handling

Date: 2026-07-30

## Inventory

- Release source: `test.sh`.
- Scope: upstream POSIX shell test suite for ex commands and vi normal mode.
- Count: 250 checks, reported by the upstream script summary.

## OHOS handling

The upstream assertions were not changed. The runner uses a copied test script
with two environment path fixes:

- `/tmp/nextvi_test_*` and `/tmp/nextvi_out_*` are redirected to the runner
  writable tmp directory because `/tmp` is read-only on the worker.
- `VI=./vi` is redirected to the freshly built/package editor binary because
  the Conan source cache does not contain `./vi`.

## Results

- Standalone upstream run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-nextvi-nextvi-7-upstream-test-r4-package-vi-and-tmp-20260730-052827-5258`
- Integrated Conan run_dir: `/storage/Users/currentUser/ohos-test-runs/codex-a-nextvi-nextvi-7-conan-r6-oldport-upstream-in-build-20260730-053111-7582`
- Result: `250 passed, 0 failed`.
- Package ref: `nextvi/7.0#d250cd421832f5670d3b1cba988f119a:6b129b068851896169fae42d399fa922d239ce8a#5861f6793785b805ffa4d2abdfa5bca8`
