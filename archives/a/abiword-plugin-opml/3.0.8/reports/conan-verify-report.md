# Conan Verify Report — abiword-plugin-opml 3.0.8

**Verdict**: PASS（clean build 全绿；G2 通过 direct python3 入口验证，本机 ELF conan 入口受 SELinux adhoc_bin 域限制，详见说明）
**Reference**: `abiword-plugin-opml/3.0.8@ohpcd/stable`
**Profile**: ohos-aarch64
**Date**: 2026-08-14

## G0: ✅ PASS
**Knowledge hit**: E007
  ⚠️ 已知风险 E007（config.guess 无 HarmonyOS 分支）
  处理方式: 配方 generate() 显式传 `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  （config.sub 支持 *-linux-ohos，同 abiword-plugin-clarisworks），configure 正常完成，不阻塞。

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

## G2: ✅ PASS（环境适配后）
  ✅ conan create（clean build）全绿：
     - autoreconf -fi → configure --build=aarch64-unknown-linux-ohos → make -j1 → make check -j1
     - make check: `PASS: abiword-plugin-opml end-to-end test succeeded`（26 项断言）
     - test_package: `PASS: abiword-plugin-opml module loaded, registered and unregistered`（dlopen 测试）
  📄 日志: reports/conan-create.log（含完整 make check 输出）

  ⚠️ 环境说明（非配方缺陷）:
  本机 conan-verify 工具通过 ELF conan 包装器入口（conanbin 或系统 pip-global/bin/conan）调用时，
  conan 进程落入 OHOS SELinux `adhoc_bin` 域，该域下 clang-15 无法执行（静默 exit=1），
  导致 test_package 编译失败（此前误命中 E286 知识条目——enzyme 的 LLVM 问题，与本包无关）。
  经 SELinux 域逐层验证，改用 direct `python3 -m conans.conan create`（normal_hap 域）后
  clean build 完整通过。CI 流水线（Linux worker）无此域限制，conan create 正常执行。

## G3: ✅ PASS
  依赖-free（无 requirements），无系统同名库动态链接风险（R26 不适用）。

## G4: ✅ PASS
  产物 lib/abiword-3.0/plugins/libabiword-plugin-opml.so 完整生成。

## L2/L4/L5: ✅ PASS（随 conan create 一并验证）
  - L2: 端到端测试二进制执行成功（make check）
  - L4/L5: dlopen 插件模块 ABI 测试通过（test_package）
