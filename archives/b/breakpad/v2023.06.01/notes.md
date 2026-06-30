# Breakpad v2023.06.01 — HarmonyOS 适配笔记

## 软件概述

Google Breakpad 是一个崩溃报告系统，包含客户端和服务器组件：
- **客户端库** (libbreakpad_client.a): 崩溃捕获、minidump 生成
- **处理库** (libbreakpad.a): minidump 解析、栈回溯、符号化
- **工具**: dump_syms（符号提取）、minidump_stackwalk（栈遍历）、minidump-2-core（转换）等

## 版本信息
- **版本**: v2023.06.01
- **源码**: https://github.com/google/breakpad/archive/refs/tags/v2023.06.01.tar.gz
- **SHA256**: 81555be3595e25e8be0fe6dd34e9490beba224296e0a8a858341e7bced67674d
- **许可证**: BSD-3-Clause
- **构建系统**: GNU Autotools (configure + make)

## 适配要点

### 1. linux_syscall_support.h (lss) 桩文件
**问题**: Breakpad 发布包不含 `linux_syscall_support.h`，该文件需从 chromium.googlesource.com 下载，但该站点在当前环境无法访问（SSL/超时/429）。

**解决**: 创建最小化桩文件 `src/third_party/lss/linux_syscall_support.h`，包含 Breakpad 源码实际使用到的所有系统调用包装函数：
- `sys_close`, `sys_open`, `sys_read`, `sys_write` 等基本 I/O
- `sys_sendmsg` 等网络操作
- `sys_mmap`, `sys_munmap` 等内存管理
- `sys_rt_sigaction`, `sys_sigaltstack` 等信号处理
- `sys_waitpid`, `sys_tgkill`, `sys_clone` 等进程管理
- `sys_ptrace`, `sys_prctl` 等调试支持
- `sys_getdents` 等目录操作

**注意事项**:
- `kernel_stat` 使用 `#define` 而非 `typedef`（源码中使用 `struct kernel_stat`）
- `sys_rt_sigaction` 直接调用 libc 的 `sigaction`，转换 `kernel_sigaction` 到 `struct sigaction`
- `sys_clone` 声明为 `extern` 函数，因为 HarmonyOS 的 `sched.h` 中未声明 `clone`

### 2. stab.h 头文件
**问题**: Breakpad 源码引用 stab.h（调试信息格式常量），但 HarmonyOS sysroot 不含此文件。

**解决**: 创建 `src/stab.h`，定义 stab 调试格式常量（N_GSYM, N_FUN, N_SO 等）。

### 3. config.guess / config.sub 补丁
**问题**: 默认 autotools 不识别 HarmonyOS 平台。

**解决**:
- config.guess: 添加 HarmonyOS 检测（识别 `*:HarmonyOS:*:*` 并映射架构到 `aarch64-unknown-linux-ohos` 等），注意需添加 `exit` 语句
- config.sub: 添加 `linux-ohos*` 到允许的 kernel-OS 组合列表（与 `linux-android*` 同行）

### 4. umask 077 修复
**问题**: configure 脚本中使用 `umask 077 && mktemp -d` 创建临时目录，在 HarmonyOS HMDFS 文件系统上生成的目录权限为 `drwx--S---`，导致后续无法在其中创建文件。

**解决**: 移除 configure 中的 `umask 077`（替换 `(umask 077 && mktemp` 为 `(mktemp` 和 `(umask 077 && mkdir` 为 `(mkdir`）。

### 5. CXXFLAGS -Wno-error=sign-compare
**问题**: HarmonyOS 系统头文件中的 `CMSG_NXTHDR` 宏实现触发 sign-compare 警告，而 Breakpad 默认开启 `-Werror`。

**解决**: 添加 `-Wno-error=sign-compare` 到 CXXFLAGS。

### 6. Google Test
**问题**: `make check` 需要 Google Test，但不包含在发布包中。

**解决**: 下载 Google Test release-1.11.0 并解压到 `src/testing/` 目录。Google Test 源码包已下载至 `/storage/Users/currentUser/googletest-1.11.0.tar.gz`。

## 构建参数
```bash
./configure --prefix=$PREFIX
make -j2 CXXFLAGS="-g -O2 -Wno-error=sign-compare"
make install DESTDIR=$TEST_PREFIX
make check
```

## 测试结果
- **编译**: ✅ 成功
- **安装**: ✅ 成功
- **make check**: 38/47 通过 (81%)
- **失败原因**: /tmp 只读文件系统限制 + lss 桩文件局限性 + 平台差异

## 依赖
- 无外部 Conan 依赖
- 需要 Google Test (仅用于 make check，不作为运行时依赖)
---

**编译结束**: 2026-06-26 10:41
**最终状态**: built
