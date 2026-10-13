/* OHOS sockaddr_storage 重复定义兼容头
 *
 * 真机（OHOS SDK 26.0.0.18）编译 src/netutils.c 等文件时报：
 *   In file included from src/netutils.h:33:
 *   .../sysroot/usr/include/linux/tcp.h:23:
 *   .../sysroot/usr/include/linux/socket.h:23:8:
 *       error: redefinition of 'sockaddr_storage'
 *   .../sysroot/usr/include/sys/socket.h:377:8:
 *       note: previous definition is here
 *
 * 根因：上游 src/netutils.h 用 HAVE_LINUX_TCP_H 分支 #include <linux/tcp.h>，
 * 而 <linux/tcp.h> 会 #include <linux/socket.h>；后者定义了
 * struct sockaddr_storage。真机的 <sys/socket.h> 也（无条件地）定义了同一个
 * 结构体，于是重复定义。
 *
 * 为什么本地 WSL 不报错：本仓库 WSL 侧的 OHOS SDK 是 musl 风格，
 * <sys/socket.h> 里该结构体被 `#ifndef __MUSL__` 包住，而 OHOS 工具链恰好
 * 预定义了 __MUSL__，因此它走 `#include <linux/socket.h>` 分支、自己不定义，
 * 冲突自然不存在。真机 SDK 没有这层保护 —— 又是只在真机口径暴露的差异。
 *
 * 修法：预先定义 <linux/socket.h> 的 include guard，使其不再重复定义
 * sockaddr_storage；<linux/tcp.h> 等仍能通过 <sys/socket.h> 拿到完整类型
 * （结构体语义等价，仅来源不同）。这是最小、无副作用的做法。
 *
 * 但屏蔽整个 <linux/socket.h> 会连它本该提供的
 *   typedef unsigned short __kernel_sa_family_t;
 * 一起丢掉。其他 UAPI 头（如 <linux/in.h>）可能依赖该类型，
 * 在个别 TU 里会变成 unknown type name。本头是 -include 全局注入的，
 * 所以这里显式补回该 typedef，与仓库既有先例一致：
 *   archives/x/xdp-tools/1.6.3/patches/0010-lib-util-params.h.patch
 *   archives/n/numactl/2.0.18/patches/0004-rtnetlink.c.patch
 */
#ifndef OHPC_OHOS_SOCKADDR_COMPAT_H
#define OHPC_OHOS_SOCKADDR_COMPAT_H
#include <sys/socket.h>
#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H 1
/* <linux/socket.h> 被上面的 guard 整体跳过，补回其关键 typedef 之一 */
#ifndef __kernel_sa_family_t_defined
#define __kernel_sa_family_t_defined 1
typedef unsigned short __kernel_sa_family_t;
#endif
#endif
#endif
