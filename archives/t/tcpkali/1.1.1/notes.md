# tcpkali 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-17
- 编译器: clang/clang++ (OHOS 交叉编译工具链 clang 15.0.4)
- 状态: published

## 编译步骤

1. 解压源码 tarball (commit 6c23ac28)
2. 从参考仓库拷贝 m4/ 和 config/ 目录到源码目录 (autoreconf -fi 所需)
3. 运行 autoreconf -fi 生成 configure 脚本
4. 运行 configure --prefix=/storage/Users/currentUser/usr/local (识别平台为 aarch64-unknown-linux-ohos)
5. 修复 config.status 中 umask 077 → umask 007 (HMDFS 权限问题)
6. 修复 config.status 中 ECHO='print -r --' → ECHO='printf %s' (bash 兼容性)
7. 运行 bash ./config.status 重新生成 Makefile 和 config.h
8. 运行 make -j1 编译
9. 运行 make install DESTDIR=/storage/Users/currentUser/tmp/test-install-tcpkali-1.1.1 staging 验证

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 不支持 ln -s 符号链接，autoreconf -fi 报错 | HMDFS 文件系统不支持符号链接 (PSCAN-HMDFS-001) | 从参考仓库直接拷贝 m4/ 和 config/ 目录，跳过需要符号链接的 autoreconf 步骤 |
| 2 | sys/sysctl.h 不存在导致编译失败 | OHOS musl libc 不提供 sys/sysctl.h 头文件 | 在 src/tcpkali_syslimits.c 中用 #ifdef HAVE_SYS_SYSCTL_H 守卫 #include <sys/sysctl.h> |
| 3 | __containerof 和 QUEUE_TYPEOF 宏缺失导致编译失败 | OHOS musl libc sys/queue.h 缺少这两个宏定义 | 在 deps/libcows/buffers.c 中添加 #include <stddef.h> 和 OHOS 兼容的 __containerof/QUEUE_TYPEOF 宏定义 |
| 4 | config.status umask 077 导致 Permission denied | HMDFS 不支持 umask 077 创建的目录（组成员无法写入） | 将 config.status 中 umask 077 替换为 umask 007 |
| 5 | config.status ECHO='print -r --' 在 bash 下不工作 | OHOS /bin/sh 是 musl-based，支持 ksh 的 print，但 bash 不支持 | 替换 ECHO 为 printf %s |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| deps/libcows/buffers.c | 添加 #include <stddef.h>；添加 OHOS 兼容 __containerof 和 QUEUE_TYPEOF 宏定义 (+14/-1) |
| src/tcpkali_syslimits.c | 用 #ifdef HAVE_SYS_SYSCTL_H 守卫 #include <sys/sysctl.h> (+2/-0) |

## 依赖版本

- ncurses 6.4 (libncurses.a 预编译静态库)
- OHOS 交叉编译工具链 clang 15.0.4

## 验证结果

### 二进制基本验证
```bash
$ file /storage/Users/currentUser/usr/local/bin/tcpkali
# ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1), not stripped
$ readelf -p .note.ohos.ident tcpkali
# [c] OHOS    ← 平台标识正确
$ readelf -d tcpkali | grep NEEDED
# NEEDED libc.so    ← 仅依赖 musl libc
```

### 功能测试（真实执行）
```bash
# 版本输出
$ tcpkali --version
tcpkali version 1.1.1 (libev)

# TCP 回环连接测试
$ tcpkali -l 12345 &  # 后台监听
$ tcpkali -c 1 -T 3s 127.0.0.1:12345
# Ramped up to 1 connections. Test duration: 3.00284 s. ✅ 通过

# 10 并发连接压力测试
$ tcpkali -c 10 -T 2s -m "hello" 127.0.0.1:12346
# Ramped up to 10 connections.
# Bandwidth per channel: 5821.822⇅ Mbps ✅ 通过

# WebSocket (RFC6455) 模式测试
$ tcpkali -l 12347 --ws &  # 后台 WebSocket 监听
$ tcpkali -c 1 -T 2s --ws 127.0.0.1:12347
# Total data sent: 154 bytes, received: 129 bytes ✅ 通过

# 消息发送与速率控制测试
$ tcpkali -c 5 -T 2s -r 10 -1 "test_start" -m "test_msg" 127.0.0.1:12348
# Total data sent: 810 bytes ✅ 通过

# staging 安装验证
$ ls test-install-tcpkali-1.1.1/.../bin/tcpkali    # 存在
$ ls test-install-tcpkali-1.1.1/.../man/man1/tcpkali.1  # 存在 (13KB)
```

完整测试报告见 `reports/test-report.md`。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/tcpkali-1.1.1-ohos-aarch64.tar.gz | 331KB | 主产物包 (ELF 签名二进制) |
| packaging/tcpkali-1.1.1-ohos-aarch64-debug.tar.gz | 72KB | debug 符号包 |

## 发现与知识

- ✅ OHOS musl libc does not provide sys/sysctl.h; guard with HAVE_SYS_SYSCTL_H (ref: E107-draft-5F18)
- ✅ OHOS musl libc lacks __containerof macro; add QUEUE_TYPEOF/__containerof definitions for sys/queue.h TAILQ_FOREACH (ref: E108-draft-740F)
- ✅ config.status uses umask 077 which blocks group write on HMDFS; patch to umask 007 (ref: E109-draft-4E6F)

## 注意事项

1. HMDFS 不支持符号链接，autoreconf 生成的文件需要从参考仓库拷贝
2. config.status 中的 umask 077 需手动改为 007 以适配 HMDFS
3. config.status 中的 ECHO='print -r --' 需改为 'printf %s' 以兼容 bash
4. OHOS musl libc 缺少 sys/sysctl.h 和 __containerof/QUEUE_TYPEOF 宏定义

---
**编译结束**: 2026-06-17 11:14
**最终状态**: built
---

**编译结束**: 2026-06-17 17:43
**最终状态**: published
