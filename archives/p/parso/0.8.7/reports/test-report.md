# parso 0.8.7 test report — task #9319

## Fixed inputs and candidate binding

- Upstream sdist: PyPI `parso-0.8.7.tar.gz`, 401,824 bytes, SHA-256 `eaaac4c9fdd5e9e8852dc778d2d7405897ec510f2a298071453e5e3a07914bb1`.
- H1-001 historical patch SHA-256: `6986452ed5c1854a194ab4039d0d6af096ded5f552aa873ac321e3b38490a6ea`.
- H1-002 historical patch SHA-256: `1f5fac5984cb941949f4bec00eff65512f0daa9a1e2c6456d3298ed11aac93eb`.
- H1-003 tested ten-file candidate patch SHA-256: `4f0c72395913379c44970651142ad98f07c85842d8791ec0f64594632423cb5a`; tested tree `ae42d0f66b91463a1acf9fc2c3637a5d4d679faf`, commit `b1e6ec9efd5426e8a413657df02d1d02abf1de5a`.
- This report was updated after H1-003. The recipe, Conan consumer, compatibility patch, and fixed source are unchanged from that tested candidate. The final W4-reviewed candidate includes documentation, statistics, and manifest metadata/status corrections; the independent audit result bound to its exact digest is `reports/audit-result.json`.

## Test case counts

The upstream suite reports an aggregate pytest count without unit/integration breakdown. The four adapted checks are counted once as distinct Conan consumer scenarios; repeated execution through Conan create and W3 does not double the count.

| Test type | Upstream count | Adapted count | Notes |
|---|---:|---:|---|
| Unit tests | Not split | Not split | Upstream does not publish a reliable category breakdown. |
| Integration tests | Not split | Not split | No unsupported classification inferred from the upstream aggregate. |
| Other upstream tests | 1,989 | 1,989 | Complete upstream `test/` pytest suite, host Python 3.11.0rc2, second captured run. |
| OpenHarmony specific tests (Conan consumer scenarios) | 0 | 4 | `packaged_import`, `grammar_resources`, `parse_and_roundtrip`, `error_recovery`; H1-003 passed 4/4. |
| **Total distinct test cases** | **1,989** | **1,993** | 1,989 upstream cases plus four target Conan consumer scenarios. |

The consumer manifest also records 10 assertions. Assertions are not counted as additional test cases. Conan create and W3 both exercised the consumer flow; the four unique scenarios are counted once.

## H1-003 OpenHarmony result

- Device: OpenHarmony aarch64, Python 3.12.9; fixed source SHA and ten-file candidate SHA are listed above.
- G0: passed. The fixed sdist was extracted, the registered patch applied, and `configure`, `make`, and `make install` completed. The install tree contained one `lib` entry and no `bin` entry, as expected for this pure Python package.
- G1: recipe integrity check passed. G2 ran a real Conan create/package/test_package flow; the produced package revision was `2d95f1e4955052d02b6264028c04958e` and package ID was `da39a3ee5e6b4b0d3255bfef95601890afd80709`.
- W3: `setup.sh` and `build_and_test.sh` passed; `.ci-result.json` recorded exit code 0. The four Conan consumer scenarios passed 4/4, and the L1e negative dependency check passed.
- Official `finish`: returned RC 1. The reported failed steps were `step5b` and `step8`; the output text `EXIT_REASON: finish_success` does not override the runner's RC 1.
- `step5b`: the global knowledge integrity check found missing fields in unrelated entries E219 (`root_cause`), E253 (`root_cause`), and E305 (`root_cause`, `rec_approach`). The parso-specific knowledge check passed. This task adds no new knowledge entry.
- `step8`: the fixed finish implementation's precheck required `packaging/` and `.staging-verified`. The fixed R19/R20 guidance deprecates that legacy packaging/staging path. This candidate does not create those obsolete artifacts or markers; the actual finish RC 1 remains disclosed, with no claim of an official waiver.
- `finalize-archive` emitted a separate RC 2 warning about legacy `packaging/` and release/debug tarballs. It was not an additional failed step. No legacy package builder or synthetic artifact was used.
- Finish also rewrote the private clone's global `SUMMARY.md` with unrelated, incorrect catalog changes and generated an unrelated feedback file. Neither is part of the ten-file candidate or this patch.

## Other test evidence and limits

- Host upstream pytest: 1,989/1,989 passed in 9.73 seconds on Python 3.11.0rc2 against the fixed sdist. This is not target-device evidence.
- Target upstream pytest was not run: the target Python 3.12.9 environment lacked pytest. No test dependency was installed or downloaded.
- The four consumer scenarios are H1-003 target evidence; prior H1-001/H1-002 consumer results remain bound to their own candidate hashes.
- Independent W4 passed for the final candidate; its exact SHA-256 binding and scope are recorded in `reports/audit-result.json`. No remote CI, push, PR, official merge, or points result is claimed here.
- Task #9319 is tagged `cpp` while the fixed upstream source is Python. The mismatch is disclosed; no tag change, blanket exemption, eligibility decision, or scoring guarantee is claimed.
