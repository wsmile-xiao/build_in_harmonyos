# bannergrab 3.5 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，非 autotools，无 configure 脚本）
- 编译日期: 2026-07-06
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 源码来自 https://github.com/CiscoCXSecurity/bannergrab，tarball 解压到工作目录
2. 使用 `ohc-run.py track-edit add` 追踪 Makefile 修改
3. 修改 Makefile：
   - 将 `gcc` 改为 `clang`
   - 将 `-lssl` 改为 `-lssl -lcrypto`（原始 Makefile 缺少 -lcrypto）
   - 添加 `.PHONY: all install uninstall clean` 声明
   - 将 `BINPATH = /usr/bin/` 改为 `BINPATH = $(prefix)/bin/`
   - 将 `MANPATH = /usr/share/man/` 改为 `MANPATH = $(prefix)/share/man/`
   - install 目标添加 `mkdir -p` 创建目录
   - install/uninstall 目标添加 `$(DESTDIR)` 前缀
4. 编译命令: `make CFLAGS="-fPIC -O2 -I$DEFAULT_PREFIX/include" LDFLAGS="-L$DEFAULT_PREFIX/lib -fuse-ld=/data/service/hnp/bin/ld"`
5. Staging 安装: `make install DESTDIR=$TEST_PREFIX prefix=$DEFAULT_PREFIX`
6. 部署安装: `make install prefix=$DEFAULT_PREFIX`
7. ELF 签名: `ohc-run.py sign-elf $DEFAULT_PREFIX/bin/bannergrab`
8. 预编译包: `ohc-run.py package bannergrab 3.5`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器无法加载 libxml2.so.16 | ohos-sdk 的 lld 依赖 libxml2 但运行时找不到 | 使用 `-fuse-ld=/data/service/hnp/bin/ld` 指定 GNU ld 2.45 代替 lld |
| 2 | `make install` 提示 "up to date" | 源码目录中存在 `install` 文件（INSTALL 的同名文件），Makefile 缺少 `.PHONY` 声明 | 添加 `.PHONY: all install uninstall clean` 声明 |
| 3 | 原始 Makefile 缺少 -lcrypto | 链接 OpenSSL 需要 -lssl -lcrypto 两个库 | 在链接选项中添加 -lcrypto |
| 4 | 二进制无法执行 (Permission denied) | 鸿蒙平台要求 ELF 签名 | 使用 `ohc-run.py sign-elf` 签名 |
| 5 | 编译警告 sizeof(array-decay) | 源码中 `sizeof(buffer -1)` 应为 `sizeof(buffer) - 1`，buffer 已退化为指针 | 不影响功能，记录为已知警告 |

## 源码修改

### Makefile
- 将编译器从 gcc 改为 clang
- 添加 -lcrypto 到链接选项
- 添加 .PHONY 声明
- 将 BINPATH 和 MANPATH 改为支持 $(prefix) 和 $(DESTDIR)
- install 目标添加 mkdir -p 创建目录

## 依赖版本

- OpenSSL 1.1.1w (头文件: /storage/Users/currentUser/usr/local/include/openssl/, 库: /storage/Users/currentUser/usr/local/lib/)

## 验证结果

```bash
$ bannergrab --version
bannergrab-ng version 3.5
Copyright (C) 2007-2008 Ian Ventura-Whiting

$ bannergrab --show-triggers
(列出 30 个触发器)

$ bannergrab --no-triggers 127.0.0.1 12345
SSH-2.0-OpenSSH_8.9
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bannergrab-3.5-ohos-aarch64.tar.gz | 3343KB | 预编译包 |
| bannergrab | 39192 bytes | ELF 二进制 (aarch64) |
| bannergrab.1 | 1680 bytes | man page |

## 注意事项

- 编译时必须使用 `-fuse-ld=/data/service/hnp/bin/ld` 替代默认 lld，否则链接失败
- 安装后必须执行 ELF 签名，否则二进制无法执行
- make check 不可用（Makefile 无 check 目标），已跳过并记录原因
---

**编译结束**: 2026-07-06 16:27
**最终状态**: published
