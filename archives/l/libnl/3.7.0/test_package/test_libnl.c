/**
 * libnl 3.7.0 smoke test — verify headers and link against libnl-3.
 */
#include <stdio.h>
#include <netlink/netlink.h>
#include <netlink/route/rtnl.h>
#include <netlink/genl/genl.h>

int main(void)
{
    int ret = 0;

    printf("libnl version: %s\n", LIBNL_VERSION);

    /* Verify we can allocate a socket handle (will fail at runtime without
     * netlink kernel support, but compilation and link are sufficient). */
    struct nl_sock *sk = nl_socket_alloc();
    if (sk) {
        printf("nl_socket_alloc: OK\n");
        nl_socket_free(sk);
    } else {
        printf("nl_socket_alloc: FAILED (expected without netlink)\n");
        ret = 1;
    }

    printf("libnl 3.7.0 smoke test: %s\n", ret == 0 ? "PASS" : "FAIL (expected without netlink)");
    return ret;
}