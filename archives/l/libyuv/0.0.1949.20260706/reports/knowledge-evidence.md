# libyuv 0.0.1949.20260706 knowledge evidence

## Scope

- Package: `libyuv/0.0.1949.20260706`
- Source: upstream commit `2dd4257364d39c38d79465c4ddc4b93137fe729b`, fetched from the GitLab mirror project archive of that same commit, pinned at SHA256 `69c3de784395ee5e527aa67e421beadbeb72beb60a55ffed70f93c8357e83040`; the 191 extracted source files match the validated snapshot one-for-one.
- Source-host history: the Chromium Gitiles `+archive` endpoint was used first, but it stamps tar entry mtimes at generation time (container SHA256 not reproducible: `00f32902…` and `2d1bd81c…` for two downloads of the same URL with byte-identical 191-file payloads), and CI build `#61999` proved the workers cannot reach `chromium.googlesource.com` at all (`ConnectTimeoutError`, connect timeout 30 s). The pinned commit exists only on Gitiles: the official GitHub mirror repository returns 404 and the GitCode mirror stops at `a09d909f…`. Three independent GitLab mirrors (projects `11344580`, `86586703`, `32947410`) return the identical 600397-byte archive for this commit, and that archive was verified to be byte-reproducible across repeated downloads.
- Validated implementation commit: `9b632b160975b469d217261d9118e49315f90edb` (gtest 1.14.0, Gitiles source). The dependency-version correction to `gtest/1.17.0` and the source-host change are pending CI re-validation on the target.
- Target: HarmonyOS 6.0, aarch64, clang 15.0.4, CMake 4.1.2, Conan 2.31.1

## Candidate extraction and deduplication

| Candidate | Trigger | Root cause | Fix and verification | Nearest knowledge | Disposition |
|---|---|---|---|---|---|
| SIMD call sites without implementation objects | Final link reports `undefined symbol: .*_NEON` and `.*_SVE2` | Compiler-visible AArch64 call sites and CMake-selected SIMD implementation sources were inconsistent | Disable NEON/SVE/SVE2 dispatch macros together and verify generic paths with upstream and consumer tests | E266 covers capability-backed implementation source selection; this case adds the verified generic fallback when optional kernels cannot be linked | Supplement E266 |

Search scope: `knowledge/`, `archives/`; terms included `CMAKE_SYSTEM_PROCESSOR`, `NEON`, `SVE2`, and `undefined symbol`. E092 covers unknown CMake platforms but not the call-site/implementation invariant. E266 is the closest mechanism.

## Evidence

| ID | Type | Input | Result | Location |
|---|---|---|---|---|
| EVID-01 | target-executed | Initial OHOS aarch64 build | Final link failed on `MergeUVRow_NEON`, `YUY2ToUVRow_SVE2`, and related symbols | run `...-092057-45327`, runner stdout |
| EVID-02 | target-executed | `CMAKE_SYSTEM_PROCESSOR=aarch64` only | Architecture object targets still absent; final link retained NEON/SVE2 undefined symbols | run `...-092300-46641`, runner stdout |
| EVID-03 | target-executed | Disable NEON/SVE/SVE2 call sites; GoogleTest 1.14.0 enabled | 3541 tests from 8 suites passed; consumer and CI gates passed | run `codex-0.0.1949.20260706-libyuv-0.0.1949.20260706-conan-20260916-095030-64960` |
| EVID-04 | registry-query | `conan list "gtest/*" -r=ohpcd`; `conan download gtest/1.14.0 -r=ohpcd --only-recipe` | Registry publishes only `gtest/1.17.0`, `1.17.0.1`, `1.17.0.2`; the declared `gtest/1.14.0` returns `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`, and CI L0i mislabels it `registry_unreachable` | 2026-09-26 local query; builds `#48566`/`#48571`/`#49081`/`#59758` all stopped at L0 |
| EVID-05 | registry-query | `conan download gtest/1.17.0 -r=ohpcd --only-recipe`; published binary `gtest/1.17.0:21b17f8b2bc0e9511e276e3d57a23893067cefe5` | Download succeeds; package contains `lib/libgtest.a`, `lib/libgtest_main.a`, `include/gtest/gtest.h`; header floor is C++17 and the CI profile already sets `compiler.cppstd=17`; upstream `unit_test/unit_test.cc` defines `main()` itself, so `gtest_main` is not required | 2026-09-26 local query |
| EVID-06 | ci-executed | Source fetch of the Gitiles archive during `conan create` | CI build `#61999` (HEAD `ba5c683120`) failed at L1: `ConnectTimeoutError ... Connection to chromium.googlesource.com timed out. (connect timeout=30)`; the runner cannot reach the upstream host, so the Gitiles URL is unusable from CI regardless of the pinned hash | build `#61999`, 2026-09-26 18:52 |
| EVID-07 | source-equivalence | GitLab mirror archive of commit `2dd42573…` (projects `11344580`, `86586703`, `32947410`) | All three mirrors return the identical 600397-byte archive, SHA256 `69c3de78…`, reproducible across repeated downloads; extraction yields the same 191 files with per-file SHA256 equal to the validated snapshot | 2026-09-26 local verification |
| EVID-08 | ci-executed | GitLab archive URL through conan `get()` during `conan create` | CI build `#62006` (HEAD `77a66fa3d1`) reached `source()` and failed with `Cannot deduce file name from the url ... Use 'filename' parameter.`; `sources.filename` is required for the `?sha=` API URL and was added. L0i in the same build reported `[ok] dependency in registry: gtest/1.17.0`, confirming the dependency correction | build `#62006`, 2026-09-26 19:05 |

Final run stdout SHA256: `776b78fc1c915b3ad4c2604db4a7652d0e59d6643950be70ee082f3634cd6ecb`.
Conan build log SHA256: `7d9d86a12dceeec3d04a21513d5bb57e3b5ec3d1976728cf6a2d7c9a39aa745b`.

## Test inventory

| Layer | Unit | Inventory | Passed | Failed | Skipped | Not run |
|---|---|---:|---:|---:|---:|---:|
| Upstream `libyuv_unittest` | GoogleTest case | 3541 | 3541 | 0 | 0 | 0 |
| Installed-package consumer | assertion | 5 | 5 | 0 | 0 | 0 |
| Destructive dependency check | scenario | 1 | 1 | 0 | 0 | 0 |

The upstream inventory was produced by 18 `unit_test/*.cc` files. No upstream test source was modified. JPEG-dependent behavior and accelerated NEON/SVE/SVE2 execution were not tested because those optional capabilities are disabled.

## File binding

| Path | Git blob at validated commit |
|---|---|
| `archives/l/libyuv/0.0.1949.20260706/conandata.yml` | GitLab-mirror archive pinned at `69c3de78…` (historical validated revisions: personal fork `97e0742…`, Gitiles `06aa1e6c…`) |
| `archives/l/libyuv/0.0.1949.20260706/conanfile.py` | `42087e9df18843b82654c4363995897714e3f2cb` (gtest 1.17.0; historical `001f837b0223da09e6f4ef366c42fbec8967a29e` was the validated gtest 1.14.0 revision) |
| `archives/l/libyuv/0.0.1949.20260706/test_package/conanfile.py` | `2b28cf01e6c2f204678df7a65f6cd1ba0a9b5319` |
| `archives/l/libyuv/0.0.1949.20260706/test_package/test.c` | `a2d0362ae99b3b4cfe2660cd5cc5ad55707cd0a1` |

The final PR adds metadata and knowledge documentation after the validated commit. Any change to the recipe, test source, dependency version, source URL, or SIMD flags requires rerunning the target validation. The `gtest/1.14.0` → `gtest/1.17.0` change and the Gitiles → GitLab source-host change are exactly such changes and are therefore pending target re-validation through platform CI; the previously recorded 3541-case result remains bound to the gtest 1.14.0 / Gitiles revision above. The source-host change does not alter the extracted payload (191 files, per-file SHA256 equal), but it is still a recipe-level change and is not claimed as pre-validated.
