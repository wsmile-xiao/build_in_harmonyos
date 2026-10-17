# ipv6toolkit 2.2 适配笔记

## 编译环境
- 构建系统: makefile（GNUmakefile，无 configure 脚本）
- 编译日期: 2026-06-16
- 编译器: clang 15.0.4 (OHOS SDK)
- 平台: HarmonyOS aarch64, musl libc
- 状态: built
- 源码 URL: https://github.com/fgont/ipv6toolkit/archive/refs/tags/v2.2.tar.gz

## 编译步骤

本项目为纯 Makefile 项目（无 configure 脚本），使用 GNUmakefile 构建。直接通过 `make` 命令编译：

1. **编译**:
   ```bash
   make PREFIX=/storage/Users/currentUser/usr/local CC=clang \
     CFLAGS="-Wall -Wno-address-of-packed-member -Wno-missing-braces -fPIC -O2" \
     CPPFLAGS="-I/storage/Users/currentUser/usr/local/include" \
     LDFLAGS="-lpcap -lm -L/storage/Users/currentUser/usr/local/lib" -j1
   ```

2. **Staging 安装（DESTDIR 模式）**:
   ```bash
   make install PREFIX=/storage/Users/currentUser/usr/local DESTDIR=/storage/Users/currentUser/tmp/test-install-ipv6toolkit-2.2
   ```

3. **本地部署**（因 /etc 为只读文件系统，从 staging 手动复制）:
   ```bash
   cp -f $STAGING_PREFIX/bin/* $DEFAULT_PREFIX/bin/
   cp -f $STAGING_PREFIX/sbin/* $DEFAULT_PREFIX/sbin/
   cp -f $STAGING_PREFIX/share/ipv6toolkit/* $DEFAULT_PREFIX/share/ipv6toolkit/
   ```

4. **单元测试**:
   ```bash
   ./tests_libipv6  # 退出码 0，全部通过
   ```

5. **打包**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py package ipv6toolkit 2.2
   # 产物: ipv6toolkit-2.2-ohos-aarch64.tar.gz (4.4MB)
   #       ipv6toolkit-2.2-ohos-aarch64-debug.tar.gz (561KB)
   ```

6. **收尾**:
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py finish ipv6toolkit 2.2 published
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sockaddr_storage` 重定义错误 | OHOS musl 系统中 `linux/socket.h` 与 `sys/socket.h` 都定义了 `sockaddr_storage`，导致编译冲突。`linux/socket.h` 使用 `_UAPI_LINUX_SOCKET_H` 作为 include guard（与标准 Linux 不同）。 | 修改 `tools/libipv6.c`: 通过 `#ifdef _SYS_SOCKET_H` 特性检测预定义 `_UAPI_LINUX_SOCKET_H` guard 跳过冲突头文件，并提供 `__kernel_sa_family_t` typedef（R8: 不使用 `#ifdef __OHOS__` 平台宏） |
| 2 | `make install` 失败：/etc 只读 | GNUmakefile 中 `ETCPATH=$(DESTDIR)/etc`，无 DESTDIR 时路径为 `/etc`（只读文件系统） | 从 staging 手动复制 binaries 和 data 到 `$DEFAULT_PREFIX`，跳过 `/etc` 配置文件安装 |

## 源码修改清单

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| tools/libipv6.c | 修正 OHOS sockaddr_storage 冲突守卫 | 使用 `#ifdef _SYS_SOCKET_H` 特性检测预定义 `_UAPI_LINUX_SOCKET_H` 跳过冲突头文件，提供 `__kernel_sa_family_t` typedef | ✅ 0001-tools-libipv6.c.patch 已生成 |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| libpcap | 1.10.6 | Conan 归档 |
| libm | musl 内置 | 系统库 |
| libc | musl | 系统库 |

## 验证结果

```bash
# 单元测试
./tests_libipv6  →  EXIT_CODE=0（全部通过）

# addr6 版本
$DEFAULT_PREFIX/bin/addr6  →  "SI6 Networks' IPv6 Toolkit 2.2"

# addr6 IPv6 地址解析
addr6 -a ::1 -q  →  ::1 ✅
addr6 -a fe80::1 -q  →  fe80::1 ✅
addr6 -a ff02::1 -q  →  ff02::1 ✅

# 全部 17 个 sbin 工具可执行（输出 usage/help 信息）
# 二进制为 aarch64 ELF 动态链接，依赖 libpcap.so + libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ipv6toolkit-2.2-ohos-aarch64.tar.gz | 4.4MB | 预编译包（含 18 个工具 + 9 个数据文件） |
| ipv6toolkit-2.2-ohos-aarch64-debug.tar.gz | 561KB | 调试符号包 |
| 0001-tools-libipv6.c.patch | — | sockaddr_storage 冲突修复补丁 |

## 注意事项

1. 大部分 sbin 工具（flow6/frag6/icmp6 等）需要 superuser 权限运行（raw socket/pcap 访问）
2. script6 是 Perl 脚本，需要 Net::IP 模块（未安装）
3. blackhole6/messi/script6 是脚本文件而非编译产物
4. 配置文件 ipv6toolkit.conf 中数据路径已硬编码为 `$DEFAULT_PREFIX/share/ipv6toolkit/`（运行时路径正确）
5. 补丁通过 `#ifdef _SYS_SOCKET_H` 特性检测预定义 `_UAPI_LINUX_SOCKET_H` guard 跳过冲突头文件，不使用 `__OHOS__` 平台宏（R8 合规）

**编译结束**: 2026-07-20 22:27
**最终状态**: built
