# Conan Verify Report — kicad-library-templates 10.0.5

**Verdict**: PASS_WITH_ENVIRONMENT_LIMITATION
**Reference**: `kicad-library-templates/10.0.5@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-20

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

## G2: ✅ PASS (direct Conan verification)
  ✅ Windows host profile: conan create succeeded; general consumer test passed
  ✅ HarmonyOS ohos-aarch64 profile: cross-compilation and test target build passed; runtime deferred by can_run()
  ✅ HarmonyOS ohos-x86_64 profile: cross-compilation and both consumer tests passed in the HarmonyOS 6.0 Huawei_2in1 VM
  📄 详细结果: archives/k/kicad-library-templates/10.0.5/notes.md

## Environment limitation
  ⚠️ The repository's fixed remote `conan-verify` worker profile could not be used from this Windows workstation because `/data/service/hnp/bin/clang` and its remote worker are unavailable.
  ℹ️ This limitation does not affect the direct host and HarmonyOS SDK/VM verification recorded above.
