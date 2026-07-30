# masscan 1.3.9 适配笔记

<!-- Adapted for HarmonyOS PC platform (arm64) -->

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-05-13
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

masscan 使用简单的 Makefile 构建，无需 configure：
1. 从 GitHub 克隆源码（https://github.com/robertdavidgraham/masscan）
2. 修改源码适配鸿蒙平台（5 个补丁）
3. 执行 `make` 编译
4. 手动安装到 staging 目录
5. ELF 签名后验证功能

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义 | linux/socket.h 与 sys/socket.h 在鸿蒙平台上冲突 | 定义 _UAPI_LINUX_SOCKET_H 宏阻止 linux/socket.h 被包含，手动定义 __kernel_sa_family_t |
| 2 | getservbyport_r 未定义 | GNU 扩展函数，鸿蒙不支持 | 修改条件编译 `#if defined(__linux__) && !defined(__TERMUX__) && !defined(__OHOS__)` |
| 3 | pthread_setaffinity_np 未定义 | GNU 扩展函数，鸿蒙不支持 | 添加鸿蒙专用分支，跳过 CPU 亲和性设置 |

## 源码修改

修改了 6 个文件，生成 6 个补丁：
1. `0001-Makefile.patch` - 修复 install 命令在 OHOS 上不可用（用 mkdir+cp 替代）
2. `0002-src-out-tcp-services.c.patch` - 修复 getservbyport_r 条件编译
3. `0003-src-pixie-threads.c.patch` - 修复 pthread_setaffinity_np 条件编译
4. `0004-src-rawsock-getif.c.patch` - 修复 sockaddr_storage 重定义
5. `0005-src-rawsock-getip6.c.patch` - 修复 sockaddr_storage 重定义
6. `0006-src-rawsock-getroute.c.patch` - 修复 sockaddr_storage 重定义

## 依赖版本

- 无外部依赖，仅需 C 编译器

## 验证结果

```bash
$ masscan --version
Masscan version 1.3.9-integration ( https://github.com/robertdavidgraham/masscan )
Compiled on: May 13 2026 17:10:44
Compiler: clang Clang 15.0.4
OS: Linux
CPU: unknown (64 bits)
GIT version: unknown
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| masscan-1.3.9-ohos-aarch64.tar.gz | 1.4M | 预编译包 |

## 注意事项

1. masscan 使用自定义 TCP/IP 栈，可能需要特殊权限
2. 首次运行需要 ELF 签名才能执行
3. 源码来自官方 GitHub 仓库 (https://github.com/robertdavidgraham/masscan)

---

**编译结束**: 2026-07-16 00:04
**最终状态**: built
