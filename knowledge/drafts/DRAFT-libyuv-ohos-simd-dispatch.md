# DRAFT-libyuv-ohos-simd-dispatch - Align optional SIMD call sites and implementation objects

On OHOS aarch64, libyuv's generic translation units exposed NEON/SVE2 dispatch call sites while the generated CMake target did not contain the matching implementation objects. The final link failed with SIMD symbol errors. Disabling the optional NEON/SVE/SVE2 paths as one unit restored the generic implementation and was verified by all 3541 upstream tests plus the installed-package consumer.

## Identity and conclusion

| Field | Value |
|---|---|
| Draft ID | `DRAFT-libyuv-ohos-simd-dispatch` |
| Structured file | `knowledge/drafts/DRAFT-libyuv-ohos-simd-dispatch.kv` |
| Status | Validated evidence awaiting review |
| Suggested destination | Supplement existing pattern E266 |
| Contributor | Theresa `<ylinzixuan@qq.com>` |
| Source task/PR | [PR #10297](https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/10297); issue pending |
| Extraction mode | New adaptation |
| Package | `libyuv/0.0.1949.20260706` |
| Upstream source | commit `2dd4257364d39c38d79465c4ddc4b93137fe729b`; fetched from the GitLab project archive of that commit, pinned at SHA256 `69c3de784395ee5e527aa67e421beadbeb72beb60a55ffed70f93c8357e83040`. The upstream Gitiles host is unreachable from the CI runners and its `+archive` container hash is generation-time dependent, so a reproducible mirror archive is pinned instead; three independent GitLab mirrors return the identical archive |
| Knowledge source commit | `9b632b160975b469d217261d9118e49315f90edb` |
| Validated commit | `9b632b160975b469d217261d9118e49315f90edb` (gtest 1.14.0); `gtest/1.17.0` dependency correction pending CI re-validation |
| Last updated | 2026-09-26 |

Validated behavior: the generic implementation builds and passes the complete enabled upstream suite on HarmonyOS 6.0 aarch64. Not proven: JPEG support or the runtime correctness/performance of NEON, SVE, or SVE2 kernels.

## 1. Trigger and signature

Target environment: clang 15.0.4 (`aarch64-unknown-linux-ohos`), CMake 4.1.2, Conan 2.31.1. The first identifiable failure was:

```text
ld.lld: error: undefined symbol: MergeUVRow_NEON
ld.lld: error: undefined symbol: YUY2ToUVRow_SVE2
ld.lld: error: undefined symbol: ARGBToYMatrixRow_NEON
```

Suggested signature: `undefined symbol: (MergeUVRow|YUY2ToUVRow|ARGBToYMatrixRow)_(NEON|SVE|SVE2)`.
It matches the two failing target runs and does not match the final successful log.

## 2. Cause and exclusions

The compiler target exposed AArch64 call sites in common sources, but CMake did not add the corresponding architecture object targets. Setting only `CMAKE_SYSTEM_PROCESSOR=aarch64` did not change that observed object inventory and the same link class remained. This excluded a missing external library: every missing symbol belonged to libyuv's own optional SIMD implementation.

## 3. Minimal fix and boundary

The recipe defines `LIBYUV_DISABLE_NEON`, `LIBYUV_DISABLE_SVE`, and `LIBYUV_DISABLE_SVE2` for both C and C++ compilation. This keeps declaration guards, dispatch call sites, and available implementation objects consistent while retaining the generic implementation.

Use this fallback only when accelerated kernels are optional and a complete target-compiler capability-based source selection cannot be supplied. If SIMD is required, follow E266 and compile the complete implementation source set after a real compiler probe.

## 4. Verification matrix

| Evidence | Type | Input | Result | Log |
|---|---|---|---|---|
| EVID-01 | target-executed | Initial recipe | NEON/SVE2 undefined symbols | run `...-092057-45327` |
| EVID-02 | target-executed | Processor metadata only | Same link class remained | run `...-092300-46641` |
| EVID-03 | target-executed | Generic SIMD fallback plus GoogleTest 1.14.0 | 3541/3541 upstream tests, consumer, L1e and L2 passed | run `...-095030-64960` |
| EVID-04 | registry-query | `gtest/1.14.0` dependency probe | Registry publishes only `gtest/1.17.0*`; the declared `1.14.0` is absent and platform CI stopped at L0 (`registry_unreachable`) | local query, 2026-09-26 |
| EVID-05 | ci-executed | Source fetch during `conan create` | CI build `#61999` could not reach the upstream Gitiles host (`ConnectTimeoutError`, 30 s); the pinned commit exists on no reachable official host | build `#61999`, 2026-09-26 |

Full evidence and log hashes are in `archives/l/libyuv/0.0.1949.20260706/reports/knowledge-evidence.md`.

### Test statistics

| Layer | Unit | Inventory | Passed | Failed | Skipped | Not run |
|---|---|---:|---:|---:|---:|---:|
| Upstream | GoogleTest case | 3541 | 3541 | 0 | 0 | 0 |
| Consumer | Assertion | 5 | 5 | 0 | 0 | 0 |
| Negative dependency check | Scenario | 1 | 1 | 0 | 0 | 0 |

No upstream test source was changed. The test executable was enabled by the recipe and linked with `gtest/1.17.0` as a build-only requirement (the originally validated run used 1.14.0, which the registry does not publish; the version correction is pending target re-validation).

## 5. Reuse boundary and forbidden shortcuts

Do not suppress linker errors, assume a processor string alone proves implementation coverage, or disable only one side of a dispatch contract. The generic fallback deliberately sacrifices optional SIMD acceleration; it does not prove that SIMD is unsupported by the hardware.

## 6. Relationship and increment

E092 covers general CMake platform recognition. E266 covers the same deeper invariant and recommends capability-backed implementation source selection. This draft adds a target-executed fallback boundary: when optional architecture objects cannot be selected reliably, disable all corresponding call sites and verify the generic behavior with upstream and consumer tests.

Search scope: `knowledge/` and `archives/`; queries included `CMAKE_SYSTEM_PROCESSOR`, `NEON`, `SVE2`, and `undefined symbol`.

## 7. Source index and checks

| Material | Reference | Role |
|---|---|---|
| Source | libyuv commit `2dd4257364d39c38d79465c4ddc4b93137fe729b` | Upstream fingerprint |
| Recipe | `archives/l/libyuv/0.0.1949.20260706/conanfile.py` at `9b632b1609` | Fix implementation |
| Consumer | `archives/l/libyuv/0.0.1949.20260706/test_package/test.c` | Installed API contract |
| Evidence | `archives/l/libyuv/0.0.1949.20260706/reports/knowledge-evidence.md` | Consolidated facts |

The PR and `source_pr` are backfilled. Recommended handling: supplement E266 with this verified generic fallback and retain the libyuv-specific report as the adaptation case.
