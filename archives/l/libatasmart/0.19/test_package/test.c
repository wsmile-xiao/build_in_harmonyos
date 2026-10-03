/* NOTE: upstream atasmart.h uses size_t without including <stddef.h>
 * (real upstream header bug); consumers must include it first. */
#include <stddef.h>
#include <atasmart.h>
#include <stdio.h>

int main(void) {
    SkDisk *d = NULL;
    /* Opening a path that does not exist must fail cleanly: proves the
     * library loads, the API is callable, and the error path is intact
     * (no real disk needed). */
    int rc = sk_disk_open("/dev/acpi-support-probe-nonexistent", &d);
    printf("sk_disk_open rc=%d d=%p\n", rc, (void *)d);

    int failures = 0;
    if (rc >= 0) {
        printf("[FAIL] expected a negative error code\n");
        ++failures;
    } else {
        printf("[ok] clean negative error code\n");
    }
    if (d != NULL) {
        printf("[FAIL] expected NULL disk on failure\n");
        sk_disk_free(d);
        ++failures;
    } else {
        printf("[ok] disk handle stays NULL on failure\n");
    }

    printf("%s: libatasmart probe (%d failures)\n", failures ? "FAIL" : "PASS", failures);
    return failures ? 1 : 0;
}
