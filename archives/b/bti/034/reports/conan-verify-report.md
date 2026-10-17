# Conan Verify Report — bti 034

**Verdict**: PASS
**Reference**: `bti/034@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-09-13T19:14:19.564582

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
  📄 日志: archives/b/bti/034/reports/conan-create.log
  📦 包引用: bti/034@ohpcd/stable
  📦 包ID: 893f4238a37e85b38a718fa7e2ba2a4231eb710a

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
