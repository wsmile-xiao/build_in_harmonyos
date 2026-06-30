# open_jtalk 1.11

# Overview
Open JTalk 是一款基于 HMM 的日语文本到语音合成系统，使用 hts_engine_API 作为语音合成引擎后端。

## Dependencies
- **hts_engine_API 1.10**: 必需的头文件和静态库
  - 编译来源: SourceForge（cmd-pkgs 预编译包中不可用）
  - 头文件: HTS_engine.h (21912 字节)
  - 静态库: libHTSEngine.a (1229532 字节)
  - 可执行文件: hts_engine (100736 字节)

## Build Patches Applied

### Patch 1: config.guess / config.sub —平台检测)
- 将 2013 版文件替换为 automake-1.17 的 2023 版本
- 目的: 支持 `aarch64-unknown-linux-ohos` triplet 检测
- 文件: 0001-config-config.guess.patch, 0002-config-config.sub.patch

### Patch 2: configure（HMDFS 兼容性）
- 移除 `umask 077` 在临时目录创建代码中
- 原因: HMDFS 文件系统忽略 umask，导致目录权限为 0700，后续无法写入文件
- 文件: 0003-configure.patch

## Configure Options
```
CONFIG_SHELL=bash bash ./configure \
  --prefix=/storage/Users/currentUser/usr/local \
  --with-hts-engine-header-path=/storage/Users/currentUser/usr/local/include \
  --with-hts-engine-library-path=/storage/Users/currentUser/usr/local/lib
```

**注意**: `/bin/sh` 是 musl-based shell，不能正确运行 autotools configure 脚本，必须使用 `CONFIG_SHELL=bash` 强制使用 bash。

## Installed Files
- `/storage/Users/currentUser/usr/local/bin/open_jtalk` — 主 TTS 可执行文件 (842304 字节, ELF64 AArch64 PIE)
- `/storage/Users/currentUser/usr/local/dic/` — MeCab-NAIST-JDic 词典数据目录
  - char.bin (262496 字节)
  - left-id.def (77672 字节)
  - matrix.bin (3792262 字节)
  - pos-id.def (1923 字节)
  - rewrite.def (7457 字节)
  - right-id.def (77672 字节)
  - sys.dic (103073776 字节, ~98MB)
  - unk.dic (5690 字节)

## Known Issues
1. 版本号显示: open_jtalk 二进制输出 "Version 1.10"，这是 hts_engine_API 的版本号，open_jtalk 自身版本为 1.11
2. 运行时需额外下载 HTS voice 模型文件（.htsvoice），不在源码包中
3. 无自动化测试套件，`make check` 无实质测试内容
4. hts_engine_API 依赖需手动编译（cmd-pkgs 中不可用），其中 HTS_misc.c 的 fpos_t 问题需修补（ftell() 替代 fgetpos 方案）

---

**编译结束**: 2026-06-16 07:39
**最终状态**: published
