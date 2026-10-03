# Conan Verify Report — k2 0_git20260430

**Verdict**: PASS
**Reference**: `k2/0_git20260430@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-10-02T04:47:20.297563

## G0: ✅ PASS
  📦 构建系统: unknown
  ℹ️ 无法识别构建系统，跳过预查询

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ export_sources() 方法
  ✅ 补丁应用调用
  ℹ️ R26: 未检测到静态链接配置（非系统同名库无需静态）
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/k/k2/0_git20260430/reports/conan-create.log
  📦 包引用: k2/0_git20260430@ohpcd/stable
  📦 包ID: 6b129b068851896169fae42d399fa922d239ce8a

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## Addendum (2026-10-02, after PR #14297 CI run)

PR CI buildbot #66779 failed at the **L0c** gate: `no_test_sources` — the CI
requires a test source file (.c/.cpp/.sh/.py) under `test_package/`, and the
original test_package drove the assertions from `conanfile.py` only. Fix
(recipe unchanged, package ID still
`6b129b068851896169fae42d399fa922d239ce8a`):

- added `test_package/test_k2.py` (consumer smoke-test runner, ympd pattern)
- `test_package/conanfile.py` now invokes it with the packaged binary path
- re-verified locally with the exact CI script (`ci/conan/build_and_test.sh`):
  L0/L1/L1e/L2/L4/L5 all pass, pass rate 100% (1/1), L1e negative test
  confirmed; fresh `conan create` → `k2 UCI tests: 3/3 passed`
  (see reports/w3-local-ci.log and reports/conan-create.log)
