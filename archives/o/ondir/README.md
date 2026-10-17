# ondir

## 简介
ondir 是一个很小的 C 命令行工具：当你在 shell 中进入或离开某个目录时，
自动执行该目录专属的脚本（例如切换 `umask`、激活/退出 virtualenv、
设置项目环境变量等）。它由 shell 钩子（`scripts.sh` / `scripts.tcsh` /
`scripts.zsh`）在每次 `cd` 时调用，ondir 读取 `~/.ondirrc`（或全局
`/etc/ondirrc`）中与路径匹配的 `enter` / `leave` 段落，把其中的命令
打印到 stdout 交给 shell `eval`。

- 上游: https://github.com/alecthomas/ondir
- 许可证: BSD-3-Clause
- 平台: OpenHarmony PC (aarch64-linux-ohos), musl, clang 15
- 构建: 手写 Makefile（无 autoconf，无外部库依赖，仅 POSIX regex.h/stat/getcwd）
- 版本状态: 0.2.3 = built（conan-verify G1-G4/L2/L4/L5 通过，test_package 18 断言全过）

## OHOS 适配（0.2.3）

- 0.2.3 上游仓库**没有 git tag**，版本以发布提交
  `cb2f9f8b21e336165fc0a310d677fda75c8e8513`（"Release 0.2.3.", 2013-09-19）为准
  （R39：github codeload 官方源码服务）。
- **clang 补丁**：Makefile 硬编码 `CC=cc` / `LD=cc`，而 OHOS musl 工具链
  只提供 `clang`（无 `cc` shim），直接 `make` 会报
  `make: cc: No such file or directory`（Error 127）。
  `patches/0001-Makefile.patch` 将编译/链接驱动改为 `clang`。
- 无第三方库依赖，配方 `requirements()` 为空。

版本索引见 `manifest.yaml`；命令行工具声明见 `commands.json`（R38）。
