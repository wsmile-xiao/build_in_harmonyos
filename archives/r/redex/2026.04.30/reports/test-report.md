# Redex 2026.04.30 — target validation report

Updated: 2026-10-09. This report separates native upstream validation, official
finish substeps and platform submission. It is not a replacement terminal.

## Native upstream and runtime validation

- Run: `redex-2026.04.30-task1092-bootstrap-v1-r2-20139-w3-r376`.
- Endpoint: `10.62.201.39:2222`; launch count/limit `1/1`.
- Candidate HEAD: `f92951d36fe04cc0073d5f588925149995ed0625`.
- Tested tree: `97503d0fad3267bd843432c28c8cc88c8268f2c6`.
- Input archive SHA-256: `ddb3eccca57465e207623dfd14f1e3c67a799d1804a4445594f0044cc36dad1f`.
- Result archive: 31,685,632 bytes, SHA-256
  `69a5ec823bcdb096bd9e79c98ff56ccae76a06c184da56eaaaed4f5a3892fec2`.
- Original frozen validator: PASS, 10/10 receipts; original release and two
  independent postrelease absence checks passed. Its remote root is deleted.

| Scope | Discovered / required | Executed PASS | Result |
|---|---:|---:|---|
| GoogleTest wrappers (149 unit + 25 integration) | 174 | 174 | PASS |
| GoogleTest leaves | 2009 | 2009 | PASS |
| Upstream Shell test | 1 | 1 | PASS |
| Conan package consumer | 1 | 1 | PASS; registered passes 120 |

The configured Automake inventory and per-binary `--gtest_list_tests` define
the denominator. Every wrapper has its own RC, XML, stdout/stderr and timeout
record; failures are collected before aggregate classification. The 174
wrappers and one Shell test are 175 independent entries, not 175 leaf tests.
No counts from earlier failed runs are added to this result. State/consumer
receipts belong only to r376's frozen input and target. The state receipt
proves `--show-passes` and `redex.py --help`, not a full APK transformation;
the independent APK consumer below closes that scope without attributing its
result to r376 or replaying the upstream suite.

## Official finish and Harmony-specific consumer

- Run: `redex-2026.04.30-task1092-official-finish-20139-r001`.
- Same endpoint, distinct task root and single launch; one official finish
  invocation. Original boot `5f0df936-15c2-4a1d-be79-201c36a5f415`.
- Candidate HEAD: same HEAD as above; tested tree
  `a48ca44d88372d4a97c5ed7f6c473b2a307f902d`.
- The tree delta from r376 is exactly four `test_package` files for the new
  Harmony coverage. Product recipe, patch and ordinary consumer bytes did not
  change. Synthetic execution commit
  `f6bf6c8d96fcbb6b40f87d2976b5be63d800c9bb` is a verification fixture, never a
  software PR commit.
- Result archive: 1,505,280 bytes, SHA-256
  `3fc2caa639c0d8b95843a0bf72d19691a4971813d526cf6a4df42c4f5557e4f3`.

The frozen runner really invoked `ohc-run.py finish redex 2026.04.30 built`
against its private repository. Official `setup.sh` and `build_and_test.sh`
passed. The original `.ci-result.json` has exit code 0, step `W3_local_ci`,
integrity `a896c51f978ed682`, and file SHA-256
`32c88ea52dad327b39d8e33a47cc9e4d57fd235ff81daf85ce464b720b1f45f7`.
It is preserved byte-for-byte; its historical remote path is not rewritten.

| Scope | Required | Actual | Result |
|---|---:|---:|---|
| Normal installed-package consumer | 1 | 1 | PASS; registered passes 120 |
| Harmony signed AArch64 HMDFS execution | 1 | 1 | PASS |

The Harmony test checks the real OHOS runtime, installed AArch64 ELF in the
HMDFS user view, nonempty `.codesign`, actual `--show-passes` execution and
unchanged executable SHA-256 before/after execution. `.codesign` was 4096
bytes. It does not prove cryptographic signature verification, rejection of
unsigned binaries, Android execution or general optimization correctness.

Original logs, each containing real consumer and Harmony PASS:

- Conan verify log: 216,804 bytes, SHA-256
  `8c50f9fc1ef68249a56de0e19444fbe8212d356fc54e20bacee5e45872ac0701`.
- Official W3 build log: 201,393 bytes, SHA-256
  `d54a1520d15dda1f39dae5a7544e4c9ce9cbf17f465e74450283be26d095c371`.

The Conan verifier reported PASS, but its G4 message could not resolve the
cache path and L2/L4/L5 were skipped. Those skips are not recast as executed
security or baseline tests. Actual package execution is independently shown
by the consumer/Harmony logs above.

## Independent installed-package APK conversion

- Run: `redex-2026.04.30-task1092-apk-consumer-20139-r003`, endpoint
  `10.62.201.39:2222`, boot `a1192107-947e-44e5-b39d-e1d5da132c34`.
- Tested HEAD: `f92951d36fe04cc0073d5f588925149995ed0625`; tested tree:
  `d92465d53c288a1151bbcbe179f5b3f8949c7e5a`. The product recipe/18 patches
  are unchanged; the delta from the official tested tree is metadata/knowledge.
- Fresh Conan create and one installed `redex.py`/`redex-all` conversion:
  RC0, timeout=false, 1/1 PASS. Original launch count/limit 1/1.
- Original frozen result: 1,013,760 bytes, SHA-256
  `61a195657f19bc007d2457a74e0d95f3e6d36ce5c8bc716f8476dd79f60523ae`.
- Original controller verified the result, removed only the exact task root,
  and completed two independent postrelease absence checks.

The 2670-byte strings APK is bound by SHA-256
`484502b5d232a3a2d95fe3965760e2ee9b82e1fca534f210c903114384c83833`.
The actual command uses the installed default.config, android.jar and the
frozen conservative `-keep class * { *; }` rules (SHA-256
`3821e3c89f3efd15a587e1cece95fec366350d22bf4639790b7da64a026798e9`),
with `--no-sign --ignore-zipalign --omit-sdk-tool-discovery`.
The same create graph supplies the external consumer's Boost/JsonCpp runtime
directories. It is not assumed to inherit Conan's child run environment.

The output APK SHA-256 is
`884544b574b0e6248f12664c4606ade8aac0e0fe8ae6b85d611fe5d34a7aec8a`.
Original validation proves ZIP CRC, DEX SHA-1/Adler-32, nonempty optimizer
statistics for 21 passes, optimizer completion log and equal input/product
before/after hashes. This is unsigned APK conversion, not evidence of Android
signing, alignment, installation/runtime semantics, optimization equivalence or
size reduction. r001's loader failure and r002's missing-keep failure remain
immutable FAILs; neither is upgraded by r003.

Dependency closures remain separately identified: native r376 and APK r003
use JsonCpp RREV `92bd5a7a9ed9d84d9dc1d4bf643dbd39`; official r001 resolved a
different published JsonCpp revision. Their receipts/logs are not merged into
one run or described as a single dependency closure.

## Aggregate failure and remaining work

r001's original terminal is **FAIL**, native finish RC **1**. Its aggregate
scope is `PARTIAL_POST_W3`, failed steps exactly `step5b,step8`: repository-wide
knowledge entries outside this software, and post-W3 report/legacy packaging
readiness. No generic RC1 waiver or terminal upgrade is applied.

After a device reboot, the original runner was absent. The original result
and a 1,385,472-byte diagnostic archive were independently collected; the
diagnostic SHA-256 is
`be923d7e520bfd30c6ac7e4dd0afb06f7257c578ef6c0ff4443da53791f2dad4`.
Exact owner-bound cleanup and postrelease 2/2 completed. Old transactions and
local archives remain immutable.

Remaining gates: current knowledge draft/deduplication, HD1-HD4 assessment,
Pre-PR v2, software PR, current-HEAD platform AI Review, platform CI and
submission readback. Archive Specification v3.0 deprecates `packaging/` and
`.staging-verified`, whereas the central submit code still tests for a tarball;
this conflict was corrected only in a user-authorized task-private submit
copy (one obsolete checklist line removed, shared framework unchanged).
Eight compatibility fixtures passed; production Pre-PR, Review and CI still
need their own actual results. No fabricated artifact/marker is used.

## Evidence location and reproducibility

Task root: `F:\HarmonyPC\redex-1092-successor-20260906`.
Original native evidence is in `production-r376` and
`r376-postw3-evidence-20261008`; official raw outputs are in
`official-finish-r001-collected-20261008`; retirement proof is in
`official-finish-r001-retirement-20261008/CLEANUP-RESULT.json`.
APK originals are preserved in `production-apk-consumer-r003`, with raw local
extraction and clearly labeled derived summaries in `postw3-collected-20261009`.
Use archived results to inspect completed tests; do not replay a consumed
run or SSH to any deleted root. Later report/knowledge changes must be
bound by a fresh candidate comparison, not attributed to the old tested tree.
