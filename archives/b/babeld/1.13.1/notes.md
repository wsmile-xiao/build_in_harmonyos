# babeld 1.13.1 适配笔记

## 编译环境
- 构建系统: makefile (纯 Makefile，无 configure 脚本)
- 编译日期: 2026-07-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: `https://github.com/jech/babeld/archive/refs/tags/babeld-1.13.1.tar.gz`
2. 下载子模块:
   - BLAKE2: `https://github.com/BLAKE2/BLAKE2/archive/refs/heads/master.tar.gz` → `BLAKE2/`
   - rfc6234: `https://github.com/bitpart-xyz/rfc6234/archive/refs/heads/main.tar.gz` → `rfc6234/` (从 reference/ 子目录提取)
3. 应用补丁: `0001-harmoneyos-fix-sockaddr-storage-redefinition.patch`
4. 编译: `make -j1`
5. 安装: `make install TARGET=$DESTDIR PREFIX=/usr/local`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义冲突 | HarmonyOS 的 linux/socket.h 与 sys/socket.h 同时定义 struct sockaddr_storage | 在 kernel_netlink.c 中 `#include <linux/netlink.h>` 之前定义 `_UAPI_LINUX_SOCKET_H`（跳过 `linux/socket.h` 的包含）并补充 `typedef unsigned short __kernel_sa_family_t` |
| 2 | GitHub source archive 不含子模块 | git archive 不包含 submodule 内容 | 在 conanfile.py source() 中单独下载 BLAKE2 和 rfc6234 |
| 3 | rfc6234 原始仓库已删除 | massar/rfc6234 返回 404 | 使用 fork bitpart-xyz/rfc6234，文件在 reference/ 目录下 |
| 4 | LD_LIBRARY_PATH 缺失 | ld.lld 找不到 libxml2.so.16 | 设置 LD_LIBRARY_PATH 包含 llvm/lib |

## 源码修改

- `patches/0001-harmoneyos-fix-sockaddr-storage-redefinition.patch`
  - 文件: `kernel_netlink.c`
  - 修改: 保留 `#include <sys/socket.h>`，在其后、`#include <linux/netlink.h>` 之前插入 `#define _UAPI_LINUX_SOCKET_H` 和 `typedef unsigned short __kernel_sa_family_t`，阻止 `linux/socket.h` 被重复包含

## 依赖版本

- 无外部库依赖，babeld 是独立二进制
- 编译器: clang 15.0 (OHOS SDK)
- 运行时仅依赖 libc.so

## 验证结果

```bash
# 版本验证
$ babeld -V
babeld-1.13.1

# 帮助信息
$ babeld -h
Usage: babeld [-V] [-l level] [-d level] ...

# 调试模式
$ babeld -D 0 -I /dev/null -L /dev/null -t eth0 -a 127.0.0.1
(正常启动，使用 SIGTERM 退出)

# 安全检查
$ checksec babeld
PIE: enabled
BIND_NOW: enabled
依赖: 仅 libc.so
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2.x 配方，使用 plain Makefile 构建 |
| conandata.yml | 源码 URL + SHA256 + 补丁引用 |
| test_package/conanfile.py | 测试包，运行 `babeld -V` 验证 |
| test_package/MANIFEST.yml | 测试声明文件 |
| patches/0001-harmoneyos-fix-sockaddr-storage-redefinition.patch | HarmonyOS 兼容性补丁 |
| reports/conan-verify-report.md | Conan 验证报告 (PASS) |
| reports/conan-create.log | Conan 构建日志 |

## 注意事项

- babeld 不是 Autotools 项目，使用纯 Makefile
- GitHub source archive 不含子模块，必须在 source() 中处理
- rfc6234 原始仓库已删除，使用 fork 时注意文件在 reference/ 目录下
- 编译时需要设置 LD_LIBRARY_PATH 包含 OHOS SDK 的 llvm/lib

---

**编译结束**: 2026-07-15
**最终状态**: built
