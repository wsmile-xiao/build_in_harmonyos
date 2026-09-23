# qcbor/1.4 adaptation notes (GLM-67, 2026-09-20)

- Platform task: 13885 (activity 6, dependency activity); registry row `qcbor-1.4` -> GLM-67.
- Branch: `feat/qcbor-1.4`; worktree `~/qzy/GLM-67-qcbor-1.4` (base f427e5be0f).
- Upstream: https://github.com/laurencelundblade/QCBOR tag `v1.4`.
- Source pin: `v1.4.tar.gz` sha256 `b8fd3813611ee14959ac815d4706c5e05123f149f05d0585761797896dd51e43` (conandata.yml).

## W0 dependency check

QCBOR is a pure C99 library with no external dependencies (only an optional
link against libm for float hardware paths). `ci/scripts/preflight_check.sh
qcbor/1.4` passed on the HarmonyOS device on 2026-09-20 ("no dependencies
need to be checked").

## W0b history and environment

- The archive tree has no qcbor entry of any version (`archives/q/` checked
  via GitCode API on 2026-09-20).
- `ohc-run.py recipe-search qcbor` found no similar recipe in the 6010-entry
  corpus; first draft generated from `templates/conanfile-cmake.py.tmpl`.
- Platform dedup: no same-name/same-version task, no open PR touching qcbor
  (scan of 11217 platform tasks and open PR titles, 2026-09-20).

## Build system analysis

- Upstream ships both a Makefile and a CMakeLists.txt
  (`cmake_minimum_required(VERSION 3.15)`; no policy injection needed).
- CMake chosen: `install(TARGETS qcbor PUBLIC_HEADER ...)` is complete, and
  the recipe only needs `cmake.install()`.
- Library sources (5): `ieee754.c`, `qcbor_decode.c`, `qcbor_encode.c`,
  `qcbor_err_to_str.c`, `UsefulBuf.c`. Public headers under `inc/qcbor/`.
- `BUILD_QCBOR_TEST=LIB` builds the `qcbor_test` static library; `=APP`
  additionally links `cmd_line_main.c`/`example.c`/`ub-example.c` into the
  `qcbortest` aggregator binary.
- Upstream registers **no `add_test()`**, so `cmake.test()` would execute 0
  cases. The recipe therefore sets `BUILD_QCBOR_TEST=APP` and executes the
  `qcbortest` aggregator directly inside `build()` (see test ledger below).

## Upstream test ledger (five dimensions)

| Dimension | Value | Basis |
|---|---|---|
| N_static | 77 | `test/run_tests.c` registry entries: `s_tests2[]` 8 + `s_tests[]` 69 (macro-definition lines excluded; grep `TEST_ENTRY(`/`TEST_ENTRY_DISABLED(` with paren anchoring) |
| N_registered | 77 | Same tables (`sizeof(s_tests2)/sizeof(test_entry2)` + `sizeof(s_tests)/sizeof(test_entry)` drive the runner loops) |
| N_executed | 75 | `qcbortest` SUMMARY inside `conan create`: "75 tests run; 0 tests failed" (after backport patch below) |
| Skipped by upstream default | 2 | `TEST_ENTRY_DISABLED`: `BigComprehensiveInputTest`, `TooLargeInputTest` — upstream marks them `enabled=false` (large-input stress cases, upstream's own choice, not an OHOS limitation) |
| N_consumer | 1 | `test_package/consumer.c` (see below) |

The run happens in `build()` (hard rule: upstream tests must execute during
the recipe build, not be merely counted). Execution details:

- E077 signing: freshly linked ELFs carry an unsigned placeholder
  `.codesign` section; the recipe strips it with `llvm-objcopy
  --remove-section .codesign`, self-signs with `binary-sign-tool` (with
  `LD_LIBRARY_PATH` removed from the signer environment), then runs it.
- OHOS exec gate: the first exec of a brand-new binary can be swallowed
  (empty stdout, rc=0); the recipe retries up to 3 times before failing.
- A non-zero aggregator exit or empty output raises `ConanException`, so a
  silent 0-execution build cannot pass.

## Consumer test (test_package)

`consumer.c` links `qcbor::qcbor` through `CMakeDeps`/`CMakeToolchain`,
encodes the CBOR map `{"greeting": "hello qcbor", "answer": 42}` with the
encoding API, decodes it back with the spiffy decode API
(`QCBORDecode_GetStringInMapSZ` / `QCBORDecode_GetInt64InMapSZ`), and asserts
string length+content equality and the int64 value; any mismatch returns
non-zero. `test()` signs the consumer binary with the same E077 flow and
retries the exec-gate swallow.

## Path A/B judgment

Path B does NOT trigger; verdict: pure Path A. Basis: the only real adaptation
work beyond a stock CMake recipe is a 3-line backport of a bug upstream
already fixed (PR #313, merged 2025-06-16, i.e. after the v1.4 release of
2024-07-11). A backport of an existing upstream fix is a per-repo patch, not
new cross-repository knowledge; the debugging approach used to locate it
(grep the registry, rerun at -O0 to rule out optimization sensitivity, search
upstream post-release fixes) reuses known experience rather than creating a
new reusable pattern, and it would fail the KB dedup/value test. No
knowledge-graph draft is filed with this PR.

### How the failing test was root-caused (record for reviewers)

- First clean build: `GetMapAndArrayTest FAILED (returned 59)` — 74 PASSED,
  rc=1 across all exec-gate retries (deterministic, not the exec gate).
- The failing assertion (return 59) compares the raw CBOR slice returned by
  `QCBORDecode_GetArray` after 5 nested indefinite arrays; the slice contents
  differed from upstream's expectation on OHOS clang.
- Rebuild at `-O0`: same failure — not optimization-dependent; a deterministic
  platform/compiler-dependent behavior difference (x86-64 upstream CI green).
- Upstream issue search: PR #313 "Fix bug due to uninitialized variable in
  qcbor_decode.c" (merged 2025-06-16, after v1.4 2024-07-11) initializes the
  `pbBreak` out-parameter in `QCBORDecode_Private_ConsumeItem`'s
  non-container branch. With `pbBreak` left uninitialized the stack-resident
  garbage changes the consume/bounds logic — exactly the observed slice
  mismatch.
- Backported the 3-line upstream fix as
  `patches/0001-backport-pr313-init-pbbreak.patch`; re-verified clean build:
  75/75 upstream tests pass on the device.

## OHOS-specific handling

- Static library by default (`shared=False`, R26); `CMAKE_SKIP_INSTALL_RPATH=ON`.
- Signing/gate handling as above.
- One source patch required: the PR #313 backport described above
  (`patch_type: portability`, `strip: 1`, applied via
  `apply_conandata_patches`).

## Verification record

- 2026-09-20, device worktree `~/qzy/GLM-67-qcbor-1.4`, CONAN_HOME
  `~/tmp/ch/home-glm67-qcbor` (isolated), profile `ci/conan/profiles/ohos-aarch64`.
- `ohc-run.py conan-verify qcbor 1.4`: Verdict PASS; G1 PASS (recipe
  completeness incl. test_package/MANIFEST.yml), G2 PASS (clean `conan create`
  from cached official tarball, patch applied, qcbortest 75/75), G3 PASS
  (consumer test package built and run: "qcbor consumer OK: 31-byte CBOR map
  round-tripped").
- Source tarball pre-seeded into the shared download cache
  (`~/tmp/ch/dlcache/s/<sha256>` + dual-URL sidecar per experience §12.39)
  after the ghfast.top mirror became unreachable; cache key/content hash
  verified before use.

### 对话记录

- 2026-09-20 GLM-67 窗口：领坑（平台任务 13885，依赖活动）→ W0 零依赖确认 → recipe-search 无相似配方 → CMake 配方首稿 → conan-verify 七轮迭代（G1 补 test_package/MANIFEST.yml；ghfast 镜像不可达改共享 dlcache 双 URL 预置并清 .dirty 后命中；GetMapAndArrayTest 失败经 O0 探针与上游 issue 检索定位为 PR #313 post-release bug 并 backport；消费者 API 按 v1.4 头文件对齐）→ Verdict PASS（75/75 + consumer 31 字节往返）→ finish → W4 审计 pass → submit。
---

**编译结束**: 2026-09-20 22:51
**最终状态**: built
