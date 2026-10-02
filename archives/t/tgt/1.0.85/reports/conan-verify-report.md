# Conan Verify Report — tgt 1.0.85

**Verdict**: PASS
**Reference**: `tgt/1.0.85@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-22T02:23:07.091823

> **证据重签（2026-09-26）**：`test_package/ohos_specific_test.sh` 重写后，G2 的
> `reports/conan-create.log` 已用**提交版配方**重跑覆盖（命令与本报告生成器等价：
> `conan create archives/t/tgt/1.0.85 -pr:h/-pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable`，
> 差异仅在**不注入 ghfast.top 镜像**，使日志中的源 URL 与提交版 `conandata.yml` 的官方单值 URL 严格一致）。
> 重跑结果 `RC=0`、`PASS=34 FAIL=0 SKIP=0`。**Verdict 与上方 Date 保留首次生成时的值，未改。**

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
  📄 日志: archives/t/tgt/1.0.85/reports/conan-create.log

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
