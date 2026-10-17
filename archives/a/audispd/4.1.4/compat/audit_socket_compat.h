/* compat/audit_socket_compat.h — 鸿蒙 socket 头冲突兼容（全局 -include）
 *
 * 鸿蒙 sysroot 的 sys/socket.h:377 与 linux/socket.h:23 都定义
 * sockaddr_storage（audit-userspace 同时 include 两者 → redefinition）。
 * 预定义 _UAPI_LINUX_SOCKET_H 让 linux/socket.h 整体跳过（不定义
 * sockaddr_storage），并手动提供 netlink.h 需要的 __kernel_sa_family_t
 * （原由 linux/socket.h 定义）。经 CFLAGS -include 强制每个编译单元先包含。
 */
#ifndef AUDIT_SOCKET_COMPAT_H
#define AUDIT_SOCKET_COMPAT_H

#ifndef _UAPI_LINUX_SOCKET_H
#define _UAPI_LINUX_SOCKET_H
typedef unsigned short __kernel_sa_family_t;
#endif

#endif /* AUDIT_SOCKET_COMPAT_H */
