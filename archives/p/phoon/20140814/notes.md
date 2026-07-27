# phoon 20140814 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile 项目，无 configure 脚本）
- 编译日期: 2026-06-15
- 编译器: clang 15.0.4 / clang++
- 平台: OpenHarmony aarch64 (musl libc, HongMeng Kernel)
- 状态: built ✅

## 编译步骤

### 1. 初始化 (`ohc-run.py init-build`)
- 源码URL: https://www.acme.com/software/phoon/phoon_14Aug2014.tar.gz
- SSL证书问题：acme.com 证书不被信任，需使用 curl -kL 下载
- tarball大小: 17KB
- 源码内容: phoon.c, date_parse.c, astro.c, date_parse.h, astro.h, phoon.1, Makefile, README
- 历史归档: 已有 built 状态的归档记录，但无 configure_options（旧格式）

### 2. Makefile 适配（代替 configure 步骤）
phoon 是纯 Makefile 项目，无 autotools configure 脚本。需手动修改 Makefile：

| 修改项 | 原值 | 新值 | 原因 |
|--------|------|------|------|
| CC | cc | clang | 系统无 cc 命令，只有 clang |
| BINDIR | /usr/local/bin | $DEFAULT_PREFIX/bin | DESTDIR 模式要求 (R20) |
| MANDIR | /usr/local/man/man1 | $DEFAULT_PREFIX/share/man/man1 | DESTDIR 模式 + man 目录规范 |
| CFLAGS | -O | -fPIC -O2 | 需要位置无关代码和优化 |
| LDFLAGS | -s | (空) | -s 会提前 strip，应由打包流程统一处理 |
| DESTDIR | 无 | DESTDIR ?= | 添加 DESTDIR 支持 (R20) |
| install目标 | 无 DESTDIR | $(DESTDIR)$(BINDIR) 等 | DESTDIR 模式 (R20) |

### 3. 编译 (`make`)
- `make -j1` 编译成功
- 9 个非致命警告（UTF-8注释编码、未使用变量、null指针转换），不影响功能
- 链接依赖: 仅 -lm（数学库）

### 4. 安装 — staging (`make install DESTDIR=$TEST_PREFIX`)
- 产物: bin/phoon (59KB) + share/man/man1/phoon.1
- DESTDIR 路径: ~/tmp/test-install-phoon-20140814/

### 5. 功能验证
- 默认运行: 显示当前月相 ✅
- 指定日期: "15 Jun 2026" 格式正确 ✅
- 不同尺寸: -l 10 / -l 20 均正常 ✅
- 错误输入: ISO格式等返回 "illegal date/time"，无崩溃 ✅

### 6. 预编译包 (`ohc-run.py package`)
- phoon-20140814-ohos-aarch64.tar.gz (84KB) — 含ELF签名、RPATH设置
- phoon-20140814-ohos-aarch64-debug.tar.gz (27KB) — debug符号包
- 预编译包二进制: 80KB (含签名比原始59KB大)

### 7. 本地安装验证 (`make install`，无 DESTDIR)
- 安装到 ~/usr/local/bin/phoon
- `phoon` 正常运行，显示月相 ASCII 图形 ✅
- ELF: 64-bit LSB arm64, dynamic, libc.so 依赖 ✅
- man page: ~/usr/local/share/man/man1/phoon.1 ✅

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载 SSL 失败 | acme.com SSL 证书不被信任 | 使用 curl -kL 手动下载，init-build 已处理 |
| 2 | 无 configure 脙本 | 纯 Makefile 项目 | 手动修改 Makefile 适配（通过补丁固化） |
| 3 | cc 未找到 | 系统无 cc 命令 | Makefile CC=clang |
| 4 | 无 DESTDIR 支持 | 原 Makefile install 无 DESTDIR | 添加 DESTDIR ?= 和修改 install 目标 |
| 5 | LDFLAGS=-s 提前 strip | 原版会直接 strip 二进制 | 移除 -s，由打包流程 strip |
| 6 | ISO日期格式不被识别 | date_parse 仅支持 "DD Mon YYYY" 格式 | 记录为软件行为，非bug |

## 补丁说明

- **0001-Makefile.patch**: 平台适配补丁
  - 修改 CC、BINDIR、MANDIR、CFLAGS、LDFLAGS
  - 添加 DESTDIR 支持
  - 类型: 平台适配 (platform_only=True)

## 依赖版本

- libc (musl): 系统自带
- libm: 系统自带（clang链接-lm）

## 二进制信息

| 属性 | 本地安装版 | 预编译包版 |
|------|-----------|-----------|
| 大小 | 59,776 字节 | 79,680 字节(含签名) |
| 类型 | ELF 64-bit LSB arm64 | ELF 64-bit LSB arm64 |
| 动态链接 | libc.so | libc.so |
| RPATH | 无 | $ORIGIN/../lib:$ORIGIN/../lib/external |
| 签名 | 未签名 | ✅ 已签名 |
---

**编译结束**: 2026-07-15 17:03
**最终状态**: built
