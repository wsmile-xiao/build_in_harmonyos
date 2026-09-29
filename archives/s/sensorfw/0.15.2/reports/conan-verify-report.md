# Conan Verify Report — sensorfw 0.15.2

**Verdict**: PASS
**Reference**: `sensorfw/0.15.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-27T04:29:11.823194

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
  📄 日志: archives/s/sensorfw/0.15.2/reports/conan-create.log
  ℹ️ 该日志为**本地复现产物，未随 PR 提交**（仓内惯例：只提交报告类文件）；G2 的关键结论已内联于
     `reports/test-report.md` —— `public headers: 180 files`、
     `Package '0b1ed271d5a43d09cfbf73bd802eb39db37e8ab9' created`、
     test_package `用例: 总 6 / 通过 6 / 失败 0`、`断言: 通过 29 / 失败 0`。

## G3: ✅ PASS
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）
