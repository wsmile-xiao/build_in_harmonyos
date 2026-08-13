# Conan Verify Report — mutt 2.4.1

**Verdict**: PASS
**Reference**: `mutt/2.4.1`
**Profile**: ohos-aarch64
**Date**: 2026-07-23

## G0: ✅ PASS
**Knowledge hit**: E007
  📦 构建系统: autotools
  ⚠️ 已知风险 E007: config.guess 不包含 HarmonyOS 检测
     方案: build() 中 inline 修改 config.guess/config.sub

## G1: ✅ PASS
  ✅ name 声明
  ✅ version 声明
  ✅ source() 方法
  ✅ build() 方法
  ✅ package() 方法
  ✅ package_info() 方法
  ✅ R26: ncurses 静态链接配置 (self.options["ncurses"].shared = False)
  ✅ conandata.yml 完整 (sources + sha256)
  ✅ test_package/ 存在 (R28)
  ✅ test_package/MANIFEST.yml 存在
  ℹ️ 无 export_sources() — patches 在 build() 内联应用 (HMDFS PATCHES/patches 冲突)

## G2: ✅ PASS
  ✅ conan create 成功 (clean build from source)
  ✅ test_package 执行: mutt -v 真实运行

## G3: ✅ PASS
  ℹ️ 无 lib/ 目录（纯可执行包）
  ✅ 无系统同名库冲突（R26 通过: ncurses 静态）

## G4: ✅ PASS
  ✅ bin/ 产物完整 (mutt, flea, muttbug, pgpewrap, smime_keys, mutt_pgpring)

## L2: ✅ PASS
  ✅ mutt --version OK
  ✅ flea --version OK
  ✅ muttbug --version OK

## L4: ✅ PASS (warn)
  ⚠️ 补丁中含危险函数 (config.guess eval 模式, 非阻塞)

## L5: ✅ PASS
  ✅ bin/ has content
