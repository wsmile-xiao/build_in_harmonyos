# libqrtr-glib 1.4.0 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-06-11
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖 glib 2.88.0（预编译包）
2. meson setup builddir --prefix=/storage/Users/currentUser/usr/local -Dintrospection=false
3. ninja
4. ninja install DESTDIR=/storage/Users/currentUser/test-install-libqrtr-glib-1.4.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义冲突 | linux/qrtr.h 包含 linux/socket.h，定义了 sockaddr_storage，与 sys/socket.h 冲突 | 创建补丁：在包含 linux/qrtr.h 前，先包含 sys/socket.h，定义 _UAPI_LINUX_SOCKET_H 防止 linux/socket.h 被包含，手动定义 __kernel_sa_family_t 和 __packed |
| 2 | gobject-introspection 缺失 | 默认启用 introspection，但缺少依赖 | 使用 -Dintrospection=false 禁用 |
| 3 | glib 链接错误（g_libintl_* 未定义） | glib 预编译包只提供静态库，缺少共享库 | 创建软链接指向 external 目录中的共享库 |
| 4 | __packed 符号重复定义 | linux/qrtr.h 使用 __packed 但未包含定义它的 sys/cdefs.h | 在补丁中包含 sys/cdefs.h，并手动定义 __packed |

## 源码修改

修改了 3 个文件以解决 sockaddr_storage 冲突：
- src/libqrtr-glib/qrtr-bus.c
- src/libqrtr-glib/qrtr-client.c
- src/libqrtr-glib/qrtr-node.c

补丁内容：
```c
/* OHOS: Prevent sockaddr_storage redefinition conflict between
 * sys/socket.h and linux/socket.h. linux/qrtr.h includes linux/socket.h
 * which defines sockaddr_storage, conflicting with sys/socket.h.
 * Solution: include sys/socket.h first, then define _UAPI_LINUX_SOCKET_H
 * to prevent linux/socket.h from being included, and manually define
 * __kernel_sa_family_t and __packed which are needed by linux/qrtr.h.
 */
#include <sys/socket.h>
#include <sys/cdefs.h>
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;
#ifndef __packed
#define __packed __attribute__((__packed__))
#endif
```

## 依赖版本

- glib/2.88.0（预编译包）

## 验证结果

编译成功，生成：
- libqrtr-glib.so.0.0.1（共享库）
- 头文件：libqrtr-glib.h, qrtr-bus.h, qrtr-client.h, qrtr-node.h, qrtr-types.h, qrtr-utils.h, qrtr-version.h
- pkgconfig: qrtr-glib.pc

无测试套件（ninja test: No tests defined）

## 知识提取记录

本次编译发现的关键知识点：
1. sockaddr_storage 重定义冲突处理方法（适用于所有包含 linux/socket.h 的代码）
2. __packed 宏需要 sys/cdefs.h 定义
3. glib 预编译包静态库 vs 共享库问题
4. meson 构建系统禁用 introspection 选项

---

**编译结束**: 2026-06-11 18:52
**最终状态**: built