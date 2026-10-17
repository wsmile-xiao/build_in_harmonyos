# Conan Verify Report — jane-street-headers 0.17.0

**Verdict**: PASS
**Reference**: `jane-street-headers/0.17.0@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-27T00:19:33.156693

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
  📄 日志: A 机 主理-72 worktree 产出，随交接按相对路径复制到 B 机本 worktree；W4 已独立复算 sha256 一致。构建主机侧 archives/j/jane-street-headers/0.17.0/reports/conan-create.log（sha256=4e17bfdda7e62ee30f0a6422f8139dc5b40d07dc9abbfccc4eff7843b8ed659a；按仓内禁入库 *.log 规则未随本 PR 提交）

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
