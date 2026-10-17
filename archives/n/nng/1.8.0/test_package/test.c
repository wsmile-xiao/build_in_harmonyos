#include <nng/nng.h>
#include <nng/protocol/pair0/pair.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    nng_socket s;
    int rc = nng_pair0_open(&s);
    if (rc != 0) {
        printf("FAIL nng_pair0_open rc=%d (%s)\n", rc, nng_strerror(rc));
        return 1;
    }
    rc = nng_close(s);
    if (rc != 0) {
        printf("FAIL nng_close rc=%d (%s)\n", rc, nng_strerror(rc));
        return 1;
    }
    const char *ver = nng_version();
    if (ver == NULL || strncmp(ver, "1.8.0", 5) != 0) {
        printf("FAIL nng_version=%s\n", ver ? ver : "(null)");
        return 1;
    }
    printf("nng %s consumer ok\n", ver);
    return 0;
}