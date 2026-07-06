# Conan Verify Report — gnu-which 2.25

**Verdict**: PASS
**Reference**: `gnu-which/2.25@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-07-03T15:21:48.517475

## G0: ✅ PASS
  📦 构建系统: autotools
  ✅ 已知风险 E007 已在配方中处理
     GNU config.guess 脚本不包含 HarmonyOS/__OHOS__ 检测分支。
uname -s 返回 HarmonyOS 无法匹配任何已知系统模式,
configure 在第一阶段就

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
  📄 日志: archives/g/gnu-which/2.25/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS (手动执行)
  ✅ which --version → "GNU which v2.25"
  ✅ which bash → /storage/Users/currentUser/usr/local/bin/bash
  Binary: ~/.conan2/p/b/gnu-wf52a413c80683/p/bin/which

## L4: ✅ PASS (手动执行)
  ✅ NX: GNU_STACK RW (non-executable stack)
  ✅ PIE: DYN (position-independent executable)
  ✅ RELRO: GNU_RELRO + BIND_NOW (full RELRO)
  Binary: ~/.conan2/p/b/gnu-wf52a413c80683/p/bin/which

## L5: ✅ PASS (手动执行)
  ✅ SHA256: bd94ada9746f148e9986e469e60dd8e55a09f023b2e7b09ffd7355b33b28a8fb
  Binary: ~/.conan2/p/b/gnu-wf52a413c80683/p/bin/which
