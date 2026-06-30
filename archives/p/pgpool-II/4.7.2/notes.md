# pgpool-II 4.7.2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++ (OHOS SDK llvm-15)
- 状态: published

## 编译步骤

1. 初始化: `python3 ohc-run.py init-build pgpool-II 4.7.2`
2. 补丁 config.guess/config.sub: 复制更新版本并应用 patch-autotools-ohos.pl
3. configure:
   ```bash
   CONFIG_SHELL=/data/service/hnp/bin/bash SHELL=/data/service/hnp/bin/bash \
   /data/service/hnp/bin/bash ./configure \
   --prefix=/storage/Users/currentUser/usr/local \
   CFLAGS="-D__MUSL__ -fPIC -O2 -Wall -Wmissing-prototypes -Wmissing-declarations -fno-strict-aliasing"
   ```
4. make -j2
5. make install DESTDIR=/storage/Users/currentUser/tmp/test-install-pgpool-II-4.7.2

### 对话 #1: 初始化与下载
- 使用 SSL_CERT_FILE 设置后成功下载 pgpool-II-4.7.2.tar.gz (5.6MB)
- 初始化创建了 .orig 和 .work 目录

### 对话 #2: config.guess/config.sub 适配
- 复制更新版本 (2026-05-17) 的 config.guess/config.sub 到 work 目录
- 应用 patch-autotools-ohos.pl 添加 __OHOS__/HarmonyOS 检测 (cg=2, sub=1 changes)
- 平台三元组: aarch64-unknown-linux-ohos

### 对话 #3: configure 运行
- 首次运行: CONFIG_SHELL=zsh → ECHO='print -r --' → config.status 报错 "print: command not found"
- 修复: CONFIG_SHELL=bash → ECHO='printf %s\n' → configure 成功

### 对话 #4: config.status Permission denied 问题
- 根因: HMDFS 文件系统 SGID 继承 + umask 077 → 创建 drwx--S--- 目录 → 文件写入失败
- 修复: 修改 configure 脚本移除 umask 077 (mktemp -d 和 mkdir)
- 创建 patch: 0001-configure-remove-umask077.patch

### 对话 #5: sockaddr_storage 重定义问题
- 根因: OHOS sysroot 中 linux/socket.h 和 sys/socket.h 都定义 sockaddr_storage
- sys/socket.h 使用 #ifndef __MUSL__ 保护，但 OHOS 编译器未定义 __MUSL__
- 修复: CFLAGS 中添加 -D__MUSL__，让 sys/socket.h 在 #ifdef __MUSL__ 分支下
  包含 linux/socket.h 并跳过自己的定义

### 对话 #6: libmd.so 缺失
- 根因: libmd 安装后缺少 libmd.so 开发符号链接 (只有 libmd.so.0 和 libmd.so.0.1.0)
- 修复: 手动创建 ln -s libmd.so.0.1.0 libmd.so

### 对话 #7: make 成功
- make -j2 编译成功，生成 pgpool 二进制和 libpgpoolpcp.so 共享库
- make install DESTDIR 模式安装成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 使用 zsh → ECHO='print -r --' → config.status 报错 | OHOS 默认 SHELL=zsh，autoconf 检测到 print 命令 | CONFIG_SHELL=/data/service/hnp/bin/bash |
| 2 | config.status "Permission denied" 写入临时文件 | HMDFS SGID 继承 + umask 077 → drwx--S--- 目录 | 0001-configure-remove-umask077.patch |
| 3 | sockaddr_storage redefinition 编译错误 | __MUSL__ 未定义 → sys/socket.h 和 linux/socket.h 都定义 | CFLAGS="-D__MUSL__" |
| 4 | clang: no such file or directory: libmd.so | libmd 开发符号链接缺失 | ln -s libmd.so.0.1.0 libmd.so |

## 源码修改

| 补丁文件 | 修改内容 | 原因 |
|---------|---------|------|
| 0001-configure-remove-umask077.patch | configure: 移除 umask 077 (mktemp -d 和 mkdir) | HMDFS SGID+umask077 权限冲突 |
| (config.guess/config.sub) | 添加 __OHOS__/HarmonyOS 检测 | 平台不识别 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libbsd | 0.11.7 | 预编译包 |
| libmd | 0.1.0 | 预编译包 |
| PostgreSQL | 16.x | 预编译包 (headers only, configure 检查) |

## 验证结果

```bash
# pgpool 二进制存在
ls /storage/Users/currentUser/tmp/test-install-pgpool-II-4.7.2/storage/Users/currentUser/usr/local/bin/pgpool
# 共享库存在
ls /storage/Users/currentUser/tmp/test-install-pgpool-II-4.7.2/storage/Users/currentUser/usr/local/lib/libpgpoolpcp.so*
# PCP 工具存在
ls /storage/Users/currentUser/tmp/test-install-pgpool-II-4.7.2/storage/Users/currentUser/usr/local/bin/pcp_*
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pgpool-II-4.7.2-ohos-aarch64.tar.gz | TBD | Release 预编译包 |
| pgpool-II-4.7.2-ohos-aarch64-debug.tar.gz | TBD | Debug 符号包 |

## 注意事项

- 必须使用 CONFIG_SHELL=/data/service/hnp/bin/bash 运行 configure
- 必须添加 -D__MUSL__ 到 CFLAGS (OHOS sysroot 的 __MUSL__ 宏缺失)
- HMDFS 文件系统 SGID 继承会导致 umask 077 创建的目录权限异常
- libmd 安装后需手动创建开发符号链接
---

**编译结束**: 2026-06-13 10:10
**最终状态**: published
