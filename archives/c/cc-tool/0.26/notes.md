# cc-tool 0.26 适配交接

## 状态

W0-W3 已完成：赛事方确认使用公开的 0.26 源码包，真机单包 CI 已通过。Issue 编号在项目文件和会话上下文中均未找到，标记为待补。

## 源码与构建分析

- 上游项目：SourceForge `cctool`，GitHub 镜像为 `scott-42/cc-tool`。
- 构建系统：Autotools（`configure.ac`、`Makefile.am`）。
- 上游依赖：Boost filesystem/program_options/system/regex/threads，以及 libusb-1.0。
- SourceForge `cc-tool-0.26-src.tgz` SHA256 为 `bb07019bf007123824c624d5d940bc0ac24184ff3b5266b04b60d64f07d40060`。
- 已增加 `0001-ohos-autotools-shell.patch`：将旧版生成 `configure/config.status` 中的 `print` 回退改为 POSIX `printf`，并修复 OHOS 上临时文件权限和 here-doc 兼容问题。
- 配方在构建阶段固定可执行 `TMPDIR`/`TMPPREFIX`，显式提供 OHOS 编译 tuple、Boost/libusb 链接参数，并保留 `make check`。

## 真机验证

- Conan 依赖：`libusb/1.0.27`、`boost/1.84.0` 均可用。
- 单包命令：`CI_PACKAGES="archives/c/cc-tool/0.26" zsh ci/conan/build_and_test.sh`。
- 运行目录：`codex-0.26-cc-tool-0.26-conan-20260915-114959-11544`。
- 结果：`conan create`、编译、链接、安装、`test_package`、负向依赖测试均通过；`L0/L1/L4/L5` 均为 pass，总计 1 成功、0 失败。
- 上游测试：已执行 `make check`，上游未注册实际测试目标，统计为 0/0。
- 启动验证：包内 `cc-tool --help` 成功输出版本 0.26 和命令帮助；该工具在没有 CC Debugger 硬件时返回 1，test_package 仅忽略此硬件相关退出码，仍明确检查包内二进制存在。

## 下一步

1. 补齐赛事 issue 编号。
2. 提交 PR 并等待赛事 PR CI 复验。
