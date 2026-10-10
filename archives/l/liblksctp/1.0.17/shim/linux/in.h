/* liblksctp OHOS/musl shim for <linux/in.h> (see socket.h for rationale).
 * src/func_tests/test_1_to_1_rtoinfo.c includes <linux/in.h> *and* <netinet/in.h>;
 * the kernel-uapi header redefines sockaddr_in/in_addr on musl.  Provide the
 * userspace definitions instead; glibc falls through to the real uapi header. */
#ifndef LIBLKSCTP_SHIM_LINUX_IN_H
#define LIBLKSCTP_SHIM_LINUX_IN_H

#ifndef __GLIBC__
#include <netinet/in.h>
#else
#include_next <linux/in.h>
#endif

#endif /* LIBLKSCTP_SHIM_LINUX_IN_H */
