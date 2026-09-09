# ncompress 5.0 适配笔记

## 软件简介
ncompress（Ncompress）是经典 Unix `compress` 的现代维护分支（Mike Frysinger / vapier 维护），
快速简单的 LZW 文件压缩工具，许可证为 Unlicense（公有领域）。

## 编译环境
- 构建系统: makefile（上游 GNUmakefile + Makefile.def，产物为单翻译单元 compress.c）
- 目标平台: OpenHarmony OHOS / aarch64
- 编译器: clang（`aarch64-unknown-linux-ohos`）
- 编译日期: 2026-09-07

## 编译步骤
源码无需 configure。等价编译命令（沿用上游选项）:
```bash
clang -O2 -g -Wall -DUSERMEM=800000 -DUTIME_H -DLSTAT -o compress compress.c
```
- `-DUSERMEM=800000`: 默认 800k 内存上限（上游 Makefile.def `options=` 注入）
- `-DUTIME_H -DLSTAT`: GNUmakefile 生成 Makefile 时注入（正确声明 `utime.h` 与 `lstat()`，
  否则现代编译器会出现隐式声明/符号链接处理问题）
- 默认不定义 `-DBYTEORDER`：走可移植的移位式位流编解码路径，大小端无关，aarch64 无需特殊处理

## 上游测试（已在 build() 中运行）
`make check` 即执行 `tests/runtests.sh`，覆盖：
- CLI 退出码/`-V`/`-h`/未知参数只走 stderr、`--` 处理
- `-c` stdin/stdout、`-d` 解压、`-f` 强制、`-k` 保留源文件
- 目录 `-r` 递归压缩/解压与续传、空文件/空目录、错误与边界路径
以可用 shell（CONFIG_SHELL/bash）运行并设 `COMPRESS=.../compress`、`TMPDIR=构建目录`。

## 打包要点
- `bin/`: compress + uncompress/zcat（程序按 argv[0] 区分模式，副本与上游硬链接等价）
  + zcmp/zdiff/zmore（上游 install_extra 安装的辅助 shell 脚本）
- `share/man/man1/`: compress.1 / uncompress.1 / zcmp.1 / zmore.1
- `licenses/`: UNLICENSE

## 遇到的问题与解决方案（将在真机验证后补充确认）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 复杂脚本不应依赖 /bin/sh 可用性 | 目标机 /bin/sh 能力不确定 | 测试脚本以 CONFIG_SHELL（bash 兜底）显式运行 |
| 2 | runtests.sh 需要绝对路径解析 | 脚本用 realpath/readlink/python | Harmony 已确认 readlink/realpath 存在，另有 python 兜底 |
| 3 | /tmp 可写性不确定 | 目标机布局 | 测试时设 TMPDIR 为 conan 构建目录 |

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

## 注意事项
- ncompress 仅 C 运行时依赖，无静态/共享库产物，无编译期依赖。
