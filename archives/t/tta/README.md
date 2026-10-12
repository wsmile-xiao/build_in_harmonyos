# tta

True Audio (TTA) lossless audio codec 的 ANSI-C 实现库，自带命令行编码/解码器。

## 功能概述

- `libtta.a`：无失真音频编解码库，提供编码器与解码器两套公开 API（编码/解码初始化、分帧/流式处理、密码保护、定位跳转等）。
- `console/tta`：命令行编码/解码工具（`tta -e|-d in out`）。

## OHOS 适配

- 打包自带的 2005 版 `config.sub` 不认识 aarch64，需打补丁接受 `aarch64-*-linux*` / `aarch64-*-ohos*`。
- 生成的 `configure` 脚本的 CPU 分支只接受 `i?86/x86_64/amd64`、`arm*`、`mipsel*`，遇到 aarch64 会直接报 "CPU aarch64 is not supported"；已把 `configure` 中 `arm*)` 改为 `arm*|aarch64*)`，将 aarch64 归入 ARM 代码路径。
- **不要**改 `configure.ac`：改动会使它比 `aclocal.m4` 新，触发 automake maintainer-mode 重新生成（需要构建环境里没有的 aclocal/automake）。
- `make install` 不安装 `libtta.h`（它只是库源文件而非 `include_HEADERS`），需在 `package()` 中手动拷贝到 include 目录。
- 上游只产出静态库（无 libtool），不接收 `--enable-static/--disable-shared` 选项。
- 上游无 formal 自动化测试（make check 0 用例，见版本级 notes 与 test_package/MANIFEST.yml 审计），但发布包自带 `console/tta` 命令行编码/解码工具；按先例将其功能验证提升为上游回归（encode/decode/roundtrip 3 用例）并在真机运行。test_package 用真实的编码→解码回环验证库 API。

## 依赖

无编译/运行依赖（纯 ANSI-C，仅 stdio/标准 C 库）。

## 参考资料

- 上游官网：http://www.true-audio.com/
- 源码包：https://downloads.sourceforge.net/project/tta/tta/libtta/libtta-2.2.tar.gz
