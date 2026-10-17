# units 2.27 适配笔记

## 变更

GNU 官方 `units-2.27.tar.gz`，SHA256 为 `e1bbdb09672e7c08eee986749e7a1629eb84a6bdf41f5a2a79d6804444abbe10`。上游使用 Autotools，配方通过 `AutotoolsToolchain` 传递 OHOS 参数并以单线程构建。

HarmonyOS PC 的 HMDFS 会把 Autoconf 生成的临时目录映射为 mode 0700，独立 HiShell 用户无法写入其中的 `subs1.awk`。配方在源码准备阶段将 `configure` 的 `umask 077` 调整为 `umask 000`，仅解决该生成目录权限问题。

## 真机验证

设备：HarmonyOS PC aarch64，独立 HiShell（uid 20020084），OHOS Clang 15，Conan 2.29.1，profile 为 `os=OHOS`、`os.version=6.0`、`arch=armv8`、`libc++`。

- `conan create`：通过（返回码 0）。
- 配方内核心换算：通过，输出 `200`。
- `test_package`：通过，`units smoke: 8 assertions passed`（8/8）。
- 验证日志：`/storage/Users/currentUser/ohpc-incoming/verify-two-units-fixed3-20260924/units/conan-create.log`。

官方 CI 和维护者审核尚未完成。

## 路径判断

按路径 A 提交；本次 `umask` 调整作为 OHOS 构建兼容修复记录。
