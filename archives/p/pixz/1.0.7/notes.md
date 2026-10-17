# pixz 1.0.7 适配笔记

## 概述

pixz 是 parallel indexed xz 压缩/解压工具，可并行处理 xz 数据，并在 tar 输入场景下生成索引，支持按路径快速抽取归档中的部分内容。

## 适配要点

- 使用官方 GitHub release 包 `pixz-1.0.7.tar.xz`。
- 依赖 `libarchive/3.8.7` 和 `xz/5.6.2`。
- 上游 configure 通过 pkg-config 查找 `libarchive` 和 `liblzma`。
- Conan 的 `xz` 包默认生成 `xz.pc`，配方在 generate 阶段复制为 `liblzma.pc`，满足上游 `PKG_CHECK_MODULES(LZMA, liblzma)`。
- 补齐 `config.guess/config.sub` 的 linux-ohos 识别。
- 修复 configure 临时目录 `umask 077` 在 OHOS storage 下可能导致的权限问题。

## 测试

- 上游测试入口：`make check`。
- 上游测试项：
  - `compress-file-permissions.sh`
  - `cppcheck-src.sh`
  - `single-file-round-trip.sh`
  - `xz-compatibility-c-option.sh`
- test_package：
  - 小文本压缩/解压 round-trip，校验输出内容一致。

## 当前状态

- 本地静态检查：通过。
- Conan export：通过。
- HarmonyOS 真机验证目标：上游 4 个测试均实际执行并通过；cppcheck 通过 `--data-dir` 使用包内 `share/Cppcheck/cfg/std.cfg`，不再跳过。
