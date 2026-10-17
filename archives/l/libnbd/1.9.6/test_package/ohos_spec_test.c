/* HarmonyOS-specific adaptation test for libnbd.
 *
 * Verifies the adapted library behaves correctly on the OHOS platform:
 *  - library version reports the packaged upstream version;
 *  - handle lifecycle (create/close) works;
 *  - API error path produces a meaningful error string (nbd_get_error)
 *    instead of crashing;
 *  - C99/C11 compilation against the public header works.
 *
 * This is a real consumer-style test: it only uses the installed public
 * header (<libnbd.h>) and public API symbols, no private internals.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libnbd.h>

static int failures = 0;
#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (!(cond)) {                                                \
            fprintf(stderr, "OHOS-TEST FAIL: %s\n", msg);             \
            failures++;                                               \
        }                                                             \
    } while (0)

int main(void) {
    /* 1. Version string from the installed package. */
    const char *ver = nbd_get_version(NULL);
    CHECK(ver != NULL && strncmp(ver, "1.9.6", 5) == 0,
          "nbd_get_version must report 1.9.6");
    if (ver)
        printf("libnbd version: %s\n", ver);

    /* 2. Handle lifecycle on OHOS. */
    struct nbd_handle *h = nbd_create();
    CHECK(h != NULL, "nbd_create must return a handle");
    if (h == NULL)
        return 1;

    /* 3. Error path: connect to a closed port; must fail gracefully and
     *    nbd_get_error() must provide a non-empty message. */
    int r = nbd_connect_tcp(h, "127.0.0.1", "1");
    CHECK(r != 0, "nbd_connect_tcp to port 1 must fail");
    const char *err = nbd_get_error();
    CHECK(err != NULL && err[0] != '\0',
          "nbd_get_error must return a non-empty message");

    /* 4. Close must be idempotent-safe (handle freed). */
    nbd_close(h);

    if (failures == 0) {
        printf("ohos-spec-test libnbd 1.9.6: PASS\n");
        return 0;
    }
    fprintf(stderr, "ohos-spec-test: %d failure(s)\n", failures);
    return 1;
}