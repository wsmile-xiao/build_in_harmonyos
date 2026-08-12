# Conan Verify Report — gnucobol 3.2

**Verdict**: PASS
**Reference**: `gnucobol/3.2@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-08-11T19:43:04.748553

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
  ✅ R26: 系统同名库静态链接配置存在
  ✅ conandata.yml 完整
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在

## G2: ✅ PASS
  ✅ conan create 成功
  📄 日志: archives/g/gnucobol/3.2/reports/conan-create.log

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
