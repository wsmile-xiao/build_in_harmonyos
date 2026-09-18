#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libnbd.h>

int main(void) {
    /* Real consumer-style validation: exercise the public API surface
     * (create/close a handle, query the library version, attempt a TCP
     * connect to a non-existent endpoint and verify the error path). */
    const char *ver = nbd_get_version(NULL);
    if (ver == NULL || strncmp(ver, "1.9.6", 5) != 0) {
        fprintf(stderr, "FAIL: unexpected libnbd version '%s'\n",
                ver ? ver : "(null)");
        return 1;
    }

    struct nbd_handle *h = nbd_create();
    if (h == NULL) {
        fprintf(stderr, "FAIL: nbd_create() returned NULL\n");
        return 1;
    }

    /* Connect to an unreachable address: must fail with an error rather
     * than crash, and nbd_get_error() must return a non-empty message. */
    int r = nbd_connect_tcp(h, "127.0.0.1", "1");
    if (r == 0) {
        fprintf(stderr, "FAIL: unexpected successful connect\n");
        nbd_close(h);
        return 1;
    }
    const char *err = nbd_get_error();
    if (err == NULL || err[0] == '\0') {
        fprintf(stderr, "FAIL: nbd_get_error() returned empty message\n");
        nbd_close(h);
        return 1;
    }

    nbd_close(h);
    printf("test libnbd 1.9.6: OK (version=%s, error path verified)\n", ver);
    return 0;
}
