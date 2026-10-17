# schedtool 1.3.0 构建记录

日期：2026-09-23。目标机：HarmonyOS / HongMeng Kernel 1.12.0，aarch64，Clang 15（target `aarch64-unknown-linux-ohos`），Conan 2.29.1。H1 运行编号 `20260923-212242-043132`；13 项输入 SHA256 全部匹配 `bundle-manifest.json`（文件 SHA256 `60efbd045a7477a3bbd14c0094449ad591a1b62afd8933ae41fad87b4aef644a`）。

Conan 配方从上游 `schedtool-1.3.0` 官方 GitHub tag 下载源归档，按 SHA256 `6c3388771849c96c4c3d4405096a3e147709ff48eb5f53adb8354735cf110500` 校验，应用两份补丁；日志明确记录 `Building from source`、包创建和 `Launching test_package`。本轮隔离 Conan cache/profile 的 host/build 均为 `os=OHOS`、`os.version=6.0`、`arch=armv8`、Clang 15；配方 `conan create` 退出码 0。原生直接构建和包内测试结果见 `reports/test-report.md`。

创建的包内 `bin/schedtool` SHA256 为 `16b8f0f126410dc62cba68eab30812e1fe7b88c64b4a502b1ff7bd8b7c7bbc58`；H1 `llvm-readelf` 核对为 ELF64 AArch64 PIE，解释器 `/lib/ld-musl-aarch64.so.1`，动态依赖 `libc.so`。源码构建、测试及 ELF 查询均在目标机运行。

以上是单文件临时 profile 下的实际 H1 验证。后续隔离完整框架 009 的正式 W3 本地 CI 又从官方源码创建 Conan 包，`setup.sh` 与 `build_and_test.sh` 均返回 0，同轮二进制 SHA256 与上述值相同，包内测试 18/18、103 断言。W3 的 L0/L1/L2/L4/L5 实际通过，但 `conan-verify` G4 找不到包 ID、其 L2/L4/L5 跳过仍错误标 PASS；完整 `finish` 在 W3 后退出 1。`built` 不代表远端官方 CI 或发布完成。
