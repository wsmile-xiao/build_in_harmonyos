/* liblksctp OHOS/musl shim for <linux/in6.h> (see socket.h for rationale).
 * src/func_tests/test_1_to_1_rtoinfo.c includes <linux/in6.h> *and* <netinet/in.h>;
 * the kernel-uapi header redefines struct in6_addr / in6addr_any on musl.
 * Provide the userspace definitions instead; glibc falls through via #include_next. */
#ifndef LIBLKSCTP_SHIM_LINUX_IN6_H
#define LIBLKSCTP_SHIM_LINUX_IN6_H

#ifndef __GLIBC__
#include <netinet/in.h>
#else
#include_next <linux/in6.h>
#endif

#endif /* LIBLKSCTP_SHIM_LINUX_IN6_H */
