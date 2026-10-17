> **状态说明（2026-09-25 追加）**：本报告记录的是 **无补丁、未执行上游测试** 的早期配方版本
> （2026-09-23）的 conan-verify 结果，作为历史留档保留。当前 PR 的配方已在该版本之后重写
> ——新增 2 个 portability 补丁，并在 `build()` 内实跑上游全量套件（67 TU / 839 用例）。
> 当前状态请以 `reports/test-report.md`、`reports/build-report.md`、
> `reports/rule4-review-remediation.md` 为准；**本文件不代表当前配方的验证结论**。

# Conan Verify Report — fatal v2026.09.14.00

**Verdict**: PASS
**Reference**: `fatal/v2026.09.14.00@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-23T12:07:52.494973

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
  📄 日志: archives/f/fatal/v2026.09.14.00/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
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
