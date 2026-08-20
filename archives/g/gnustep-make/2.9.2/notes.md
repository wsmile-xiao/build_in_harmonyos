# gnustep-make 2.9.2 适配笔记

- 构建系统：Autotools
- 目标平台：HarmonyOS PC aarch64
- 源码：`https://codeload.github.com/gnustep/tools-make/tar.gz/refs/tags/make-2_9_2`
- SHA256：`b3fdee058879675f6979c553fb6172b160ca79ffd0f170f51379326b7922941a`

## 补丁

- `0001-config.guess.patch`：识别 HarmonyOS 主机并生成 `aarch64-unknown-linux-ohos`。
- `0002-config.sub.patch`：接受 `linux-ohos` 系统三元组。
- `0003-configure.patch`：在 hmdfs 构建目录使用 `umask 022`，并在系统没有 `chown` 时跳过可选属主设置。

## 测试

上游源码没有顶层 `make check` 目标。`TestFramework` 的 Objective-C 示例需要 GNUstep Foundation（由后续 gnustep-base 提供），因此没有伪造上游测试结果。Conan consumer test 真实调用已安装的 `gnustep-config` 三个接口：`GNUSTEP_MAKEFILES`、`GNUSTEP_CONFIG_FILE` 和 `--objc-flags`。
---

**编译结束**: 2026-08-19 18:18
**最终状态**: built
