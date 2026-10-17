# pkgconf 3.0.5 test report

**Test date**: 2026-08-17
**Target**: OpenHarmony 6.0, arm64, Clang 15

## Result

- Build status: passed
- Upstream tests: 586/586 (100%)
- Added assertions: 26/26 (100%)

## Upstream inventory

| Inventory | Passed | Total |
| --- | ---: | ---: |
| API executables | 15 | 15 |
| Fixture files in 14 suites | 425 | 425 |
| Capability-gated OOM test | 1 | 1 |
| Parser corpus inputs | 141 | 141 |
| Solver corpus inputs | 3 | 3 |
| Missing-corpus negative test | 1 | 1 |
| Total | 586 | 586 |

The hash-bound upstream evidence registers the same 33 top-level names and a
canonical map of 425 unique `(suite, fixture)` keys. Every selected fixture
terminal is a real `PASS`; skipped and failed official entries are both zero.
The missing-corpus negative is bound to `EXPECTEDFAIL`, return code 1,
`REPLAYED_INPUTS=0`, and the missing-path stderr marker. The corpus runners
reported `REPLAYED_INPUTS=141` and `REPLAYED_INPUTS=3`.

Evidence SHA-256: unified result
`f3c7029a538002e43d4927a3f3ec696b1305642d012adff58653c27f635c4209`;
`tmpfile()` directed result
`62772c1fdb2b0da62335d66a6dfa70370de601581b08481f78c3417fd65cded4`;
target projection
`b31139faa13ee6d81c43772396ffe7baf8eb0c044870553dc5584e030ed30502`;
production-gate matrix
`a901fce014e3b79d307bee5c06b0a0ef669e8d700662a9cece370c6946e91c5c`.

## Conan package

- Semantic-baseline RREV: `4a3f062deb7823efabd171c60b7aab22`
- Package ID: `21b17f8b2bc0e9511e276e3d57a23893067cefe5`
- PREV: `7dad25c18ecf6400f17f94e2df9542ce`
- Root recipe forced from source: yes
- Compatible binary reuse: none
- Consumer compile and link: passed
- Fresh isolated r20 OHOS/arm64 semantic-baseline `conan create`: passed; seven patches exported,
  43 primary targets and 125 validation targets compiled; log SHA-256
  `06c0a7ff041987ac4c64c4c391e1f7aea39f7382a2ca844ed4abe7e8b3f5833d`.
- Local CI: passed (1/1 package; L0, L1, L1e, and L5 passed; L4's only
  warning is the scanner's `targets`/`gets` substring false positive)
- Targeted negatives: upstream terminal/projection gate 19/19; overflow shim
  ENOMEM 1/1; static OOM boundary expected failure 1/1; `shared=True`
  invalid-state contract 1/1; Meson introspection build-environment matrix
  13/13.

## Artifact closure

- Commands: `pkgconf`, `bomtool`, `spdxtool`, `pccritic`
- Command format: ELF64, AArch64, musl interpreter
- Dynamic dependencies: `libc.so` only
- Static library: `lib/libpkgconf.a`, 21 object files
- Public headers: 5
- `lib/pkgconfig/libpkgconf.pc`: present
- `bin/pkg-config`: absent as required

The added consumer test contains 26 assertions over the library API and four
installed commands. Its cross-build compilation and link completed, and the
same candidate snapshot passed all 26 assertions on the authorized device.

## Authorized device validation

- Endpoint: `10.62.215.229:2222`
- Run ID: `pkgconf-3.0.5-task3321-bootstrap-v1-r2-215229-w3-r36`
- HEAD/tree/base: `0eee6166980ad3d2f7449048cd9c5ea77e0d7d48` /
  `0a17ebc2b9c6dc8add9eebc42be8bbe73805d0cf` /
  `5fd3b60374894bc2dd93a00fb51213a1a8c990d3`
- Controller launches: 1; runner launches: 1; runner RC: 0
- Signed ELF inputs: 5; target assertions: 26/26
- Release: root process 0, clean scans 2, lock 0, lease 0; postrelease passed
- Readback tar: 1,427,968 bytes, SHA-256
  `83856bf764a71f75d59755b3c88047337a0b66b6c5fb27e829f33fcb64bbc7fb`
- Postrelease reconciliation: 48/48 members, 13/13 evidence hashes, directed
  validator matrix 7/7; result SHA-256
  `ba0f3db2512013a4ecd8a3095c2536bc34889a58e6b3355ef0d9b664ab9d56fe`

The frozen host validator failed only after the successful target terminal,
release, and postrelease because its regular-file-shaped regex rejected the
expected archive-root directory record. The immutable failure remains
preserved; the target transaction was not relaunched.

## Current candidate W3 input rebind

The CI source fallback now keeps both source URLs on HTTPS; the downloaded
426972-byte authority mirror archive retains the official SHA-256, while the
patch descriptions gain only repository-required numeric prefixes. The later
CI repairs move Meson introspection into Conan's explicit `conanbuild` build scope
and add one test-only patch whose targets are limited to four `tests/api/`
files. A fail-closed successor verifier accepts only those exact changes and
the current upstream/direct-test evidence. Eleven of thirteen CI inputs equal
the r20 Conan validation copy byte-for-byte; `conandata.yml` is source-byte
equivalent. The submitted 0007 wrapper differs
only in unified-diff representation; Git, GNU patch `--fuzz=0`, and patch_ng
produce the same complete 755-file post-image as the semantic baseline. Of the
24 package files, all 23 runtime/content
files are byte-identical to historical W3; only Conan's generated
`conanmanifest.txt` changes with the recipe revision.

The fresh consumer compiles and links against the current exact package, but
its bytes are not claimed identical to the historical consumer. The verifier
instead keeps the immutable r36 consumer/run evidence bound to unchanged
`test_package` sources, exact installed runtime bytes, one controller/runner
launch, runner RC0, 26/26 assertions, and clean release. Its positive/negative
matrix passed 12/12 and rejects any CI-input, patch-scope, matrix, upstream,
package-content, or historical-terminal drift. This is a no-device
current-input rebind; r36 was not relaunched. The machine-readable report is
`reports/w3-current-input-rebind.json`.

## Platform CI repair

Buildbot build #26332, buildid 29163, proved source retrieval and the main
43-target build succeed on the CI worker. Its second Meson setup also succeeded
through `self.run`, then the first direct `subprocess.run(["meson", ...])`
failed with `FileNotFoundError` because it bypassed Conan's generated build
environment. The repaired production methods capture Meson JSON with
`self.run(..., env="conanbuild", scope="build")`, raise on every nonzero
result, and retain all inventory/projection gates. The directed matrix passed
13/13.

Buildbot build #26630, buildid 29515, then compiled all 43 primary targets and
all 125 validation targets before `api-audit`, `api-buffer`, and `api-fileio`
failed because libc `tmpfile()` returned `NULL` despite the writable test
`TMPDIR`. Patch 0007 replaces the seven affected test call sites with a
portable anonymous-stream helper using `mkstemp + unlink + fdopen`. Its
directed matrix passed 6/6 with 7/7 call sites and zero residue; the complete
official inventory passed 586/586.

Buildbot build #26988, buildid 29985, bound PR #5532 and exact revision
`98ac0f366d755b37c8f019073c7c0e7be97ba801`. It completed source retrieval,
43 primary targets, 125 validation targets, the official 586/586 inventory,
packaging, and consumer compilation/linking. It then stopped before runtime
because the Worker lacked `llvm-objcopy`, `llvm-readelf`, and
`binary-sign-tool`. The repaired `test_package` requires the consumer and all
four command artifacts before capability gating, reports runtime as `NOT_RUN`
only for the absent tool set, and preserves the original signed 26-assertion
path when the tools exist. Missing artifacts and every execution/signing error
remain fatal. The production-entry directed matrix passed 7/7, including both
`can_run(false)` artifact-order boundaries; replacement
exact-current-HEAD CI remains pending.
