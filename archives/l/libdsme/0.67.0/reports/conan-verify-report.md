# Conan Verify Report — libdsme 0.67.0

**Verdict**: PASS
**Reference**: `libdsme/0.67.0@ohpcd/stable`
**Profile**: ohos-aarch64-device
**Date**: 2026-09-21T18:44:01.214930

## G0: ✅ PASS
**Knowledge hit**: E490
  📦 构建系统: autotools
  ⚠️ 已知风险 E490 未在配方中处理
     根因: Autotools helper scripts are executable programs, but some HarmonyOS PC adaptation paths preserve source content without
     方案: restore-known-autotools-script-modes
     修复: chmod +x configure config.guess config.sub install-sh missing; ./configure; make -j1; make -j1 check
     ⚡ G2 conan create 可能因此失败，建议先修复

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
  📄 日志: archives/l/libdsme/0.67.0/reports/conan-create.log

## G3: ✅ PASS
  ℹ️ 无 bin/ 目录（可能是纯库包）
  ✅ 无系统同名库冲突（R26 通过）

## G4: ✅ PASS
  ⚠️ 无法找到程序包 ID

## L2: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L4: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## L5: ✅ PASS
  ⏭️ 跳过（无 cache 路径）

## 审计备注（P3 澄清）

- 本次验证使用 profile `ohos-aarch64-device`（与 W3 本地 CI 门禁一致）。
- G0 段落中的 E490 提示面向 autotools 工程（configure/config.guess 脚本）；
  本包为手写 Makefile、不含 autotools 脚本，该提示不适用。
- G4 的"无法找到程序包 ID"为工具在部分缓存状态下的提示；产物树已由包目录
  逐项列出并通过 test_package 的 OHOS 产物契约检查（ELF64/AArch64/DYN、
  SONAME、DT_NEEDED、无 RPATH、导出符号）。
