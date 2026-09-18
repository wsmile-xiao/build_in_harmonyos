/*
 * Consumer test for libdontdie 1.2.0.
 *
 * The library exposes no API: it hooks socket(2) via LD_PRELOAD and
 * switches on TCP keepalive.  This consumer therefore only needs the
 * libc socket API; the assertions verify the library's behaviour:
 *   1. socket() succeeds;
 *   2. SO_KEEPALIVE is enabled on the freshly created socket;
 *   3. TCP_KEEPALIVE equals the DD_TCP_KEEPALIVE_TIME value the
 *      library was configured with (7, set by test_package).
 */
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>

int main(void) {
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("FAIL: socket()");
        return 1;
    }

    int on = 0;
    socklen_t len = sizeof(on);
    if (getsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &on, &len) != 0) {
        perror("FAIL: getsockopt(SO_KEEPALIVE)");
        return 2;
    }
    if (!on) {
        fprintf(stderr, "FAIL: SO_KEEPALIVE not enabled by libdontdie\n");
        return 3;
    }

    int secs = 0;
    len = sizeof(secs);
    /* Upstream maps DD_TCP_KEEPALIVE_TIME onto TCP_KEEPIDLE
     * (src/libdontdie.c SET_SOCK_OPT(time, "TIME", TCP_KEEPIDLE)). */
    if (getsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &secs, &len) != 0) {
        perror("FAIL: getsockopt(TCP_KEEPIDLE)");
        return 4;
    }
    const char *want = getenv("DD_TCP_KEEPALIVE_TIME");
    int want_secs = want ? atoi(want) : 7200;
    if (secs != want_secs) {
        fprintf(stderr, "FAIL: TCP_KEEPIDLE=%d, expected %d\n", secs, want_secs);
        return 5;
    }

    close(fd);
    printf("dd_consumer OK: SO_KEEPALIVE=1, TCP_KEEPIDLE=%d\n", secs);
    return 0;
}
