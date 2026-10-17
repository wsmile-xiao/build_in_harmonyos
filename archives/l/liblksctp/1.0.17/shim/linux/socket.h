/* liblksctp OHOS/musl shim for <linux/socket.h>.
 *
 * The HarmonyOS SDK's <linux/socket.h> line 23 redefines `struct sockaddr_storage`,
 * which musl's <sys/socket.h> already provides.  The upstream src/func_tests/*.c
 * include BOTH <sys/socket.h> and <linux/socket.h>, so they fail to compile with
 * "error: redefinition of 'sockaddr_storage'".
 *
 * We shadow the kernel-uapi header with the userspace definition of record by
 * prepending this shim directory to the include path (-I, see conanfile.py
 * generate()).  Feature detection is by libc family: on glibc we fall through to
 * the real uapi header via #include_next, so the shim is a no-op there.
 * Upstream sources are left untouched (R8).
 */
#ifndef LIBLKSCTP_SHIM_LINUX_SOCKET_H
#define LIBLKSCTP_SHIM_LINUX_SOCKET_H

#ifndef __GLIBC__
#include <sys/socket.h>
#else
#include_next <linux/socket.h>
#endif

#endif /* LIBLKSCTP_SHIM_LINUX_SOCKET_H */
