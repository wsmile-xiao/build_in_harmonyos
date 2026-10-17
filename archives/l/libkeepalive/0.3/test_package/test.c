/* Consumer-side verification program for libkeepalive.
 *
 * Opens an AF_INET TCP socket and reports the effective TCP keepalive state, so
 * that the very same binary can be executed with and without
 * LD_PRELOAD=libkeepalive.so and the two runs can be compared.
 *
 * Usage: test_libkeepalive <mode>
 *   off   SO_KEEPALIVE must be disabled
 *   on    SO_KEEPALIVE must be enabled
 *   tune  SO_KEEPALIVE enabled and TCP_KEEPCNT / TCP_KEEPIDLE / TCP_KEEPINTVL
 *         must be the values requested through the environment variables
 *
 * Exit status: 0 = every assertion passed, 1 = an assertion failed.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

static int read_int_option(int fd, int level, int option)
{
    int value = -1;
    socklen_t len = sizeof(value);

    if (getsockopt(fd, level, option, &value, &len) != 0) {
        perror("getsockopt");
        close(fd);
        exit(EXIT_FAILURE);
    }
    return value;
}

#define CHECK(cond, ...)                              \
    do {                                              \
        if (!(cond)) {                                \
            fprintf(stderr, "FAIL: " __VA_ARGS__);    \
            fprintf(stderr, "\n");                    \
            close(fd);                                \
            return EXIT_FAILURE;                      \
        }                                             \
    } while (0)

int main(int argc, char **argv)
{
    const char *mode = (argc > 1) ? argv[1] : "off";
    int expect_on = strcmp(mode, "off") != 0;
    int fd;
    int keepalive;
    int value;

    fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (fd < 0) {
        perror("socket");
        return EXIT_FAILURE;
    }

    keepalive = read_int_option(fd, SOL_SOCKET, SO_KEEPALIVE);
    printf("mode=%s SO_KEEPALIVE=%s\n", mode, keepalive ? "ON" : "OFF");
    CHECK(keepalive == expect_on,
          "mode=%s: SO_KEEPALIVE is %s, expected %s",
          mode, keepalive ? "ON" : "OFF", expect_on ? "ON" : "OFF");

    if (keepalive && strcmp(mode, "tune") == 0) {
#ifdef TCP_KEEPCNT
        value = read_int_option(fd, IPPROTO_TCP, TCP_KEEPCNT);
        printf("TCP_KEEPCNT=%d\n", value);
        CHECK(value == 7, "mode=tune: TCP_KEEPCNT=%d, expected 7", value);
#endif
#ifdef TCP_KEEPIDLE
        value = read_int_option(fd, IPPROTO_TCP, TCP_KEEPIDLE);
        printf("TCP_KEEPIDLE=%d\n", value);
        CHECK(value == 42, "mode=tune: TCP_KEEPIDLE=%d, expected 42", value);
#endif
#ifdef TCP_KEEPINTVL
        value = read_int_option(fd, IPPROTO_TCP, TCP_KEEPINTVL);
        printf("TCP_KEEPINTVL=%d\n", value);
        CHECK(value == 13, "mode=tune: TCP_KEEPINTVL=%d, expected 13", value);
#endif
    }

    close(fd);
    printf("PASS\n");
    return EXIT_SUCCESS;
}
