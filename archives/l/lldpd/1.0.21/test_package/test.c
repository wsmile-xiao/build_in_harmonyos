/* test.c — liblldpctl API smoke test (offline, no running lldpd needed)
 *
 * Exercises the public liblldpctl connection lifecycle and error-handling API:
 *   - lldpctl_get_default_transport(): default Unix control socket path
 *   - lldpctl_strerror(): translate an error code to a human string
 *   - lldpctl_new()/lldpctl_release(): allocate/free a connection
 *   - lldpctl_last_error(): a freshly created connection has no pending error
 *
 * lldpctl_new(NULL, NULL, NULL) only allocates the connection handle and an
 * internal self-pipe; it does not connect to the daemon socket until a request
 * is actually sent (sync_send/sync_recv connect lazily). Hence this test runs
 * without a running lldpd.
 */
#include <lldpctl.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>

#define CHECK(cond)                                                            \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s (%s:%d)\n", #cond, __FILE__, __LINE__);  \
            return 1;                                                          \
        }                                                                      \
    } while (0)

int main(void)
{
    /* 1. Default transport socket path must be a non-empty string. */
    const char *transport = lldpctl_get_default_transport();
    CHECK(transport != NULL);
    CHECK(transport[0] != '\0');
    printf("default transport: %s\n", transport);

    /* 2. strerror must translate a known error code to a non-empty string. */
    const char *msg = lldpctl_strerror(LLDPCTL_ERR_CANNOT_CONNECT);
    CHECK(msg != NULL);
    CHECK(msg[0] != '\0');
    printf("strerror(CANNOT_CONNECT): %s\n", msg);
    /* The same code reported by last_error must map to the same message. */
    CHECK(strcmp(lldpctl_strerror(LLDPCTL_NO_ERROR), msg) != 0);

    /* 3. Allocate a connection handle with the default synchronous transport. */
    lldpctl_conn_t *conn = lldpctl_new(NULL, NULL, NULL);
    CHECK(conn != NULL);

    /* 4. A freshly allocated connection reports no error. */
    lldpctl_error_t err = lldpctl_last_error(conn);
    CHECK(err == LLDPCTL_NO_ERROR);

    /* 5. Release frees the connection and returns 0. */
    int rc = lldpctl_release(conn);
    CHECK(rc == 0);

    printf("liblldpctl API test passed\n");
    return 0;
}
