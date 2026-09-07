# Conan Verify Report — afmize 2.0.2

**Verdict**: PARTIAL (G0-G3 PASS; G4/L2/L4/L5 NOT_RUN)
**Reference**: `afmize/2.0.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-04T19:03:51.510251

## G0: ✅ PASS
  📦 构建系统: cmake
  ✅ 已知风险 E092 已在配方中处理
     CMake 不认识 HarmonyOS 作为目标平台，
没有对应的 platform module。
当 CMake 检测到系统名称为 harmonyos/ohos 时，
无法匹配任何已知平台（Lin

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
  📄 证据: archives/a/afmize/2.0.2/reports/conan-cpp17-summary.md

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ⏭️ NOT_RUN
  Conan verifier did not expose a cache path/package ID for this run. The exact W3 package identity and package contents are recorded in `conan-cpp17-summary.md`; no G4 PASS is claimed here.

## L2: ⏭️ NOT_RUN
  No platform smoke-test command was executed by this verifier; the CTest and test_package results are recorded separately.

## L4: ⏭️ NOT_RUN
  No checksec scan was executed by this verifier.

## L5: ⏭️ NOT_RUN
  No package baseline comparison was executed by this verifier.
