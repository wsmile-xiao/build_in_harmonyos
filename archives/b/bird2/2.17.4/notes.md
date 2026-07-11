# 编译笔记 — bird2 2.17.4 for OpenHarmony

## 软件概述

BIRD (BIRD Internet Routing Daemon) 是一个功能强大的动态 IP 路由守护进程，支持 BGP、OSPF、RIP、Babel、BFD 等多种路由协议。它设计用于 Linux 和其他类 Unix 系统，在开源社区中广泛使用。

- **官网**: https://bird.network.cz/
- **版本**: 2.17.4
- **许可证**: GPL-2.0-or-later
- **源码**: https://gitlab.nic.cz/labs/bird/-/archive/v2.17.4/bird-v2.17.4.tar.gz

## 构建系统

bird2 使用 GNU Autotools 构建系统（configure.ac + Makefile.in）。源码包仅包含 configure.ac，需要先运行 autoconf 和 autoheader 生成 configure 脚本和 sysdep/autoconf.h.in。

## OHOS 平台适配

### E007: config.guess 不识别 HarmonyOS

**问题**: 源码包含的 config.guess 版本为 2018-03-08，不识别 HarmonyOS (`uname -s` 返回 "HarmonyOS")，导致 configure 无法猜测构建类型。

**修复**: 在 conanfile.py 的 build() 方法中，将 tools/config.guess 和 tools/config.sub 替换为自包含的 OHOS 感知版本，输出 `aarch64-unknown-linux-ohos` 三元组。

### E091: sockaddr_storage 重定义

**问题**: OHOS 内核头文件 linux/socket.h 定义了 struct sockaddr_storage，与 musl libc 的 sys/socket.h 冲突。当源码同时包含 sys/socket.h 和 linux/netlink.h（间接包含 linux/socket.h）时，产生重定义错误。

**修复**: 在 CFLAGS 中添加 `-D__MUSL__` 宏定义，触发 musl libc 的头文件守卫机制，避免重复定义。

### HMDFS umask 077 权限问题

**问题**: autoconf 生成的 configure 脚本在 config.status 中设置 `umask 077`，创建的临时目录权限为 0700。在 OHOS HMDFS 文件系统上，这些权限导致 "Permission denied" 错误，config.status 无法正常运行。

**修复**: 在 autoconf 生成 configure 后，将 configure 脚本中的 `umask 077` 替换为 `umask 022`，使 config.status 使用更宽松的权限。

### 无 ncurses 头文件

**问题**: bird2 的客户端工具 (birdcl) 需要 ncurses 库，OHOS 平台不提供 ncurses 开发头文件。

**修复**: 使用 `--disable-client` 配置选项跳过客户端编译。注意 birdcl 仍会编译（它是一个简单的命令行工具，不需要 ncurses），只是不需要 ncurses 的客户端功能被禁用。

### OHOS SDK sysroot 包含路径

**问题**: bird2 需要 Linux UAPI 内核头文件（如 linux/rtnetlink.h、linux/mpls.h），这些头文件位于 OHOS SDK sysroot 中。

**修复**: 在 CFLAGS 中添加：
- `-I$OHOS_SYSROOT/usr/include`
- `-I$OHOS_SYSROOT/usr/include/aarch64-linux-ohos`

## 编译过程

1. **autoconf**: 从 configure.ac 生成 configure 脚本
2. **autoheader**: 从 configure.ac 生成 sysdep/autoconf.h.in
3. **configure**: 检测系统特性，生成 Makefile 和 config.h
4. **make -j1**: 编译所有源文件，链接生成 bird 和 birdcl 二进制
5. **make install**: 安装到指定前缀
6. **make check**: 运行 22 个单元测试

## 测试结果

- **make check**: 22/22 测试通过
- **bird --version**: BIRD version 2.17.4 ✅
- **bird -p (配置解析)**: 成功解析默认和自定义配置 ✅
- **birdcl**: 正常尝试连接控制 socket（需守护进程运行）⚠️

## 产物

- `bin/bird`: BIRD 路由守护进程 (1,968,640 bytes, ELF aarch64)
- `bin/birdcl`: BIRD 控制客户端 (59,776 bytes, ELF aarch64)
- `etc/bird.conf`: 示例配置文件

## 依赖

- musl libc (系统提供)
- 无外部库依赖

## 注意事项

1. `prctl(PR_SET_THP_DISABLE)` 在 OHOS 上失败是已知行为，不影响功能。
2. bird 守护进程需要 root 权限和网络命名空间才能正常运行。
3. birdcl 需要 bird 守护进程运行后才能连接控制 socket。
4. `filter_test` 使用相对路径 `filter/test.conf` 查找配置文件，在 out-of-source 构建中需将测试配置文件从源码目录复制到构建目录。
---

**编译结束**: 2026-07-06 18:56
**最终状态**: built
