/* Consumer test for libcontra: links the packaged shared library and
 * exercises the real public API declared in libcontra.h, plus a real
 * socket() call (the family of calls this library interposes).
 */
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>

#include <libcontra.h>

static int failures = 0;
static int checks = 0;

#define CHECK(desc, cond) do { \
    checks++; \
    if (cond) { printf("PASS: %s\n", desc); } \
    else { printf("FAIL: %s\n", desc); failures++; } \
} while (0)

int main(void) {
    const char *s;
    int fd;

    /* Must not crash; only reads CONTRA_* environment variables. */
    libcontra_init();
    printf("PASS: libcontra_init() callable\n");
    checks++;

    s = libcontra_af2string(AF_INET);
    CHECK("af2string(AF_INET) mentions IP protocol family",
          s != NULL && strstr(s, "IP protocol family") != NULL);

    s = libcontra_af2string(AF_INET6);
    CHECK("af2string(AF_INET6) mentions version 6",
          s != NULL && strstr(s, "version 6") != NULL);

    s = libcontra_sock2string(SOCK_STREAM);
    CHECK("sock2string(SOCK_STREAM) mentions Sequenced",
          s != NULL && strstr(s, "Sequenced") != NULL);

    s = libcontra_sock2string(SOCK_DGRAM);
    CHECK("sock2string(SOCK_DGRAM) returns non-NULL", s != NULL);

    s = libcontra_oname2string(SO_REUSEADDR);
    CHECK("oname2string(SO_REUSEADDR) mentions Reuse",
          s != NULL && strstr(s, "Reuse") != NULL);

    fd = socket(AF_INET, SOCK_STREAM, 0);
    CHECK("socket(AF_INET, SOCK_STREAM, 0) succeeds", fd >= 0);
    if (fd >= 0) {
        close(fd);
    }

    printf("libcontra consumer test: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
