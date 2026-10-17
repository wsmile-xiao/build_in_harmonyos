# jane-street-headers 0.17.0 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 real device
- Clang 15 (OHOS aarch64 profile, ci/conan/profiles/ohos-aarch64)
- Conan 2.29.1

## Verification

- `conan-verify jane-street-headers 0.17.0`: exit 0 — section headers show ✅ PASS; Verdict: PASS. Subrows: G0 build system unknown (pre-query skipped), G1/G2/G3 passed, G4 warns no package ID (header-library tooling limitation).
  (report: reports/conan-verify-report.md; create log: A 机 主理-72 worktree 产出，随交接按相对路径复制到 B 机本 worktree；W4 已独立复算 sha256 一致。构建主机侧 reports/conan-create.log，sha256=4e17bfdda7e62ee30f0a6422f8139dc5b40d07dc9abbfccc4eff7843b8ed659a，按禁入库 *.log 未随本 PR 提交)
- L2/L4/L5: skipped by tooling (no cache path; no binary cache artifacts to smoke/sign/baseline)
- `finish jane-street-headers 0.17.0 built`: W3 local CI conan create exit 0,
  W2 structural checks pass, R36 dependency check pass (no dependencies),
  PR atomicity: recipe-only changes (13 files), JUNK_PR_DIFF single-package scope

## test_package

The consumer TU compiles against the packaged headers via CMake
`find_package(jane-street-headers CONFIG REQUIRED)`, then executes and checks
the upstream contracts:

- compile-time: `static_assert(THREAD_IO_CUTOFF == 65536)` (core_params.h)
- compile-time: `__unused` attribute-shim presence guard (jane_common.h)
- runtime: constant check + `./test_jane_street_headers` real execution,
  output `jane-street-headers consumer ok`, exit 0

- Test cases: 1 (3 assertions)
- Passed: 1
- Failed: 0
- Skipped: 0

Five-dimension ledger: upstream static total 0 / upstream executable 0 /
consumer executed 1 passed 1 / skipped 0 / failed 0.

## Upstream tests

Upstream ships no test suite: the tag archive has no tests/ directory and the
Makefile only wires dune build/install helpers (`default`, `install`,
`uninstall`, `reinstall`, `clean`). Static inventory: 0 (R51 evidence recorded in
test_package/MANIFEST.yml and notes.md). The Conan consumer test is the
applicable validation (R34).

## Result

The header-only package was verified on an OpenHarmony aarch64 device and is
eligible for built status. Official competition CI remains the final platform
validation.
