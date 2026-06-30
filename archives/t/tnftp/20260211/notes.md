# tnftp 20260211 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang 15.0.4 (OpenHarmony 工具链)
- 状态: published

## 编译步骤

1. 下载源码: `tnftp-20260211.tar.gz` from NetBSD CDN
2. 解压并初始化构建环境
3. 更新 `buildaux/config.guess` 和 `buildaux/config.sub` (E007: 旧版本无法识别 HarmonyOS)
4. 在 `libnetbsd/` 中新增 `getpass.c` 替代实现
5. 修改 `Makefile.in`: 在 LIBOBJS/LTLIBOBJS 中追加 `getpass$U.o` / `getpass$U.lo`
6. 修改 `libnetbsd/Makefile.in`: 同上，LIBOBJS/LTLIBOBJS 追加 getpass；libnetbsd_la_LIBADD/libnetbsd_la_DEPENDENCIES 使用 $(LTLIBOBJS)
7. 运行 `sh ./configure --prefix=$DEFAULT_PREFIX --enable-ssl --enable-ipv6`
8. `make -j1` 编译
9. `make install DESTDIR=$TEST_PREFIX` staging 安装

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | 2018年版本的 config.guess 不支持 HarmonyOS 平台 | 替换为 hints/ 目录中的 2025 版本 config.guess/config.sub |
| 2 | `undefined reference to getpass` | musl libc 不提供 getpass() GNU 扩展函数 | 在 libnetbsd/ 中提供 getpass.c 替代实现，并在 Makefile.in 的 LIBOBJS/LTLIBOBJS 中追加 getpass |
| 3 | autoreconf 生成的 configure 不兼容 toybox sh | autoreconf 生成的 configure 脚本含复杂引号语法，toybox /bin/sh 报 "no closing quote" | 保留原始 configure 脚本（兼容 toybox），直接 patch Makefile.in 而不使用 autoreconf |
| 4 | G0 clean-verify configure_options 解析错误 | manifest.yaml 中 configure_options 为 YAML 列表格式，G0 regex 提取时截断引号导致 "no closing quote" | 改为简单字符串格式: `configure_options: "--enable-ssl --enable-ipv6"` |
| 5 | tnftp_config.h 被作为补丁生成 | tnftp_config.h 是 configure 生成的产物，不应出现在补丁中 | 从 work 目录中移除，refresh-patch 不再包含此文件 |
| 6 | /bin/sh ./configure "C compiler cannot create executables" | 手动运行 configure 时缺少正确的环境变量（CC, CFLAGS, LDFLAGS 等） | ohc-run.py build 脚本通过 zsh shell 正确设置环境变量执行 configure |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁 |
|------|------|------|------|
| buildaux/config.guess | 平台检测(E007) | 替换为 2025 版本 | 0004-buildaux-config.guess.patch |
| buildaux/config.sub | 平台检测(E007) | 替换为 2025 版本 | 0005-buildaux-config.sub.patch |
| libnetbsd/getpass.c | getpass 缺失替代实现 | 新增文件，使用 termios 实现 | 0003-libnetbsd-getpass.c.patch |
| Makefile.in | LIBOBJS 需包含 getpass | LIBOBJS/LTLIBOBJS 追加 getpass$U.o/getpass$U.lo | 0001-Makefile.in.patch |
| libnetbsd/Makefile.in | LIBOBJS 需包含 getpass | LIBOBJS/LTLIBOBJS 追加 getpass$U.o/getpass$U.lo | 0002-libnetbsd-Makefile.in.patch |

## 对话记录

### Round 1: 初始编译尝试
- configure: `sh ./configure --prefix=/storage/Users/currentUser/usr/local --enable-ssl --enable-ipv6`
- 编译耗时: ~2分钟
- getpass.lo 编译成功，tnftp 二进制正常生成
- G0 clean-verify 初始失败 (configure_options 格式问题)

### Round 2: 修复补丁和 G0 验证
- 清理 work 目录中的生成文件（tnftp_config.h, .pre-scan-report.yaml 等）
- 重做 .orig 目录（从原始 tarball 重新解压）
- regenerate patches: 5 个核心补丁（Makefile.in, libnetbsd/Makefile.in, libnetbsd/getpass.c, config.guess, config.sub）
- 修复 manifest.yaml configure_options 格式
- G0 clean-verify 通过 ✅

## 依赖版本

- libedit: 3.1 (系统 libedit，非内置)
- ncurses: 6.5
- openssl: 3.x (SSL support enabled)

## 验证结果

- G0 干净构建验证: ✅ 通过 (2026-06-17)
- tnftp 二进制: ELF 64-bit aarch64, 动态链接
- 功能: tnftp 是交互式 FTP 客户端，无 --version 参数，无测试套件

## 注意事项

- tnftp 无测试套件 (make check = all-am)
- getpass() 在 musl/OHOS 上不可用，需要替代实现
- 保留原始 configure 脚本（不使用 autoreconf），因为 autoreconf 生成的脚本不兼容 toybox /bin/sh
- G0 clean-verify 使用 /bin/sh ./configure，原始 configure 兼容 toybox sh

---
**编译结束**: 2026-06-17
**最终状态**: published
---

**编译结束**: 2026-06-17 08:38
**最终状态**: published
