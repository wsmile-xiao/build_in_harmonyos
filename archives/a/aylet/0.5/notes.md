# aylet 0.5 适配笔记

## 编译环境

- 构建系统：makefile
- 编译日期：2026-08-24
- 编译器：aarch64-unknown-linux-ohos Clang 15.0.4
- Conan：2.29.1（OHOS aarch64 profile）
- 状态：built（真实 OHOS 交叉编译、Conan 验证和 W3 通过，尚未上传制品仓）

## 编译步骤

```bash
conan create archives/a/aylet/0.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=.conan2/profiles/default --build=aylet/*
```

host profile 提供 OHOS SDK 的 `tools.build:compiler_executables:c`；配方在 OHOS
场景为该编译器追加 `-static`。必须显式指定 `aylet` 目标，否则 Makefile 默认
目标会继续构建依赖 GTK 的 `xaylet`。

## 遇到的问题与解决方案

| 问题 | 根因 | 解决方案 |
|---|---|---|
| OSS 后端包含 `sys/soundcard.h` | OHOS SDK 没有 OSS 头文件 | 增加 stdout PCM 后端并通过 `OBJS` 选择它 |
| curses UI 包含 `curses.h` 且 OHOS SDK 没有目标 ncurses 开发文件 | stdout 模式本来就不需要交互 UI | 增加无 curses 的 `ui-stdout.c`，保留原无 UI 状态与信号处理 |
| `ui.c` 使用 `exit` 但未包含标准库头 | 上游老代码与现代 C 编译器不兼容 | 构建时使用 `-include stdlib.h` |
| CI 的 `test_package` 环境没有名为 `cc` 的命令 | 测试包硬编码调用主机命令名 | 从 Conan profile 读取 `tools.build:compiler_executables:c`，OHOS 下静态编译测试执行器 |
| WSL 初始没有 `zsh` | 仓库 W3 固定使用 `zsh ci/conan/setup.sh` | 安装 WSL 的 `zsh` 后按同一 W3 路径验证 |
| OHOS SDK 没有动态加载器 | WSL 没有设备侧 `/lib/ld-musl-aarch64.so.1` | OHOS 构建使用 `-static`，再由 qemu/binfmt 执行 |

## 源码修改

`0001-drv-stdout.c.patch`：增加无 OSS/OpenBSD 依赖的 stdout 音频后端；不提供原生音频设备播放。
`0002-headless-ui.patch`：为 stdout 模式提供无 curses 的 UI 实现，保留无 UI 播放循环、状态输出和 Ctrl-C 处理。

## 依赖

配方没有额外 Conan `requires`；stdout 模式不链接 ncurses。

## 验证结果

- `conan-verify`：G1/G2/G3 及本地 L2/L4/L5 检查通过；G4 在发布前没有远端制品 ID。
- Conan `test_package`：使用 Conan profile 编译器构建测试执行器，实际执行打包后的 `aylet -h`，并用最小合法 AY 文件确认 stdout PCM 输出非空。
- 本轮 `conan-verify`：recipe 检查通过；host=OHOS、build=WSL Linux 的干净 Conan 构建通过；未把尚未发布的本地缓存当作远端制品。
- 本轮 W3：L0、L1、L4、L5 通过；L2 对不支持的长选项 `--help/--version` 给出非阻塞跳过，短选项 `-h` 已由 test_package 验证。
- 产物为静态 aarch64 ELF，可由 WSL 的 qemu/binfmt 执行。

## 已知限制

- stdout 后端输出 PCM 数据，不等同于 OHOS 原生音频设备播放。
- stdout 模式不依赖 `ncurses`；交互式 curses UI 不在本次 OHOS 适配范围内。

## 编译结束

- 最终状态：built
- 编译结束日期：2026-08-24
