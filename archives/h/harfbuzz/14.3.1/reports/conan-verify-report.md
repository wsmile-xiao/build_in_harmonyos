# Conan Verify Report — harfbuzz 14.3.1

**Verdict**: PARTIAL — G1-G3 and the G2 `conan create` passed; G0 was a
build-system detector false positive, while G4/L2/L4/L5 were not executed by
this report. The separate W3 and local finish evidence remain authoritative.
**Reference**: `harfbuzz/14.3.1@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-08-19T11:56:56.202852

## G0: NOT APPLICABLE — detector false positive

The recipe uses Meson, not Autotools. The generated E007 `config.guess`
warning does not apply to this candidate and is not counted as a PASS gate.

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
  📄 日志: archives/h/harfbuzz/14.3.1/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: NOT RUN
  ⚠️ 此报告未解析到程序包 ID，不能据此声明产物完整性通过。

## L2: NOT RUN
  ⏭️ 此报告无 cache 路径，未执行 smoke test。

## L4: NOT RUN
  ⏭️ 此报告无 cache 路径，未执行安全扫描。

## L5: NOT RUN
  ⏭️ 此报告无 cache 路径，未执行产物基线检查。

## Evidence boundary

This corrected metadata report does not replace the actual OHOS/arm64 W3,
75/75 upstream Meson test, shared-package identity, or 1/1 consumer evidence.
Those results remain bound by `.ci-result.json`, `w3-validation-result.json`,
and `local-finish-result.json`.
