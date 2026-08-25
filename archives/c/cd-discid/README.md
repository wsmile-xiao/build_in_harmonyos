# cd-discid

## 简介

cd-discid 是一个 CDDB discid 查询后端工具，从 CD-ROM 光盘读取 TOC（节目表）并输出 CDDB disc id。最初为 cdgrab（现 abcde）设计，可被任何需要 CDDB 数据的程序使用。

## 版本信息

- **当前版本**: 1.0.0（上游 tag=1.0）
- **作者**: Robert Woodcock <rcw@debian.org>、Timur Birsh <taem@linukz.org>
- **官网**: https://github.com/taem/cd-discid

## 功能特性

1. **CDDB discid 生成**: 读取 CD TOC，输出 32 位十六进制 CDDB disc-id、音轨数、各音轨帧偏移、唱片总长度
2. **跨平台**: 支持 Linux、FreeBSD、OpenBSD、NetBSD、Solaris、macOS
3. **极简依赖**: 纯单文件 C，仅使用 libc + ioctl，无任何外部库

## 编译说明

### 编译要求

- C 编译器（OHOS 使用 clang）
- make

### 构建系统

纯 Makefile 工程，无 configure 脚本、无 autotools：

```
make CC=clang -j1     # 编译 cd-discid
make install          # 安装（上游用 /usr/bin/install，OHOS 无此工具，配方内改为直接 copy）
make check            # 不存在！上游仅 all/clean/install/tarball 四个目标
```

## OHOS 适配要点

- 编译选项从 Conan conf（`tools.build:compiler_executables`）获取，不依赖 shell 环境变量（R33）
- `make install` 依赖 `/usr/bin/install` 且 `-o 0` 需要 root 权限，Conan 配方在 `package()` 中直接复制产物
- 无 CD-ROM 设备的沙箱环境下，二进制走 open 错误/Usage 消息路径退出；test_package 据此做真实运行行为验证
