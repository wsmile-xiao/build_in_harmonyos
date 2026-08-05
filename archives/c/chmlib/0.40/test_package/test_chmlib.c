#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <chm_lib.h>

int main(void)
{
    int failures = 0;

    /* Test 1: chm_open on non-existent file returns NULL */
    struct chmFile *h = chm_open("/nonexistent/chmlib_test_does_not_exist.chm");
    if (h != NULL) {
        fprintf(stderr, "FAIL 1: chm_open returned non-NULL for non-existent file\n");
        chm_close(h);
        failures++;
    } else {
        printf("PASS 1: chm_open correctly returned NULL\n");
    }

    /* Test 2: open a minimal ITSF file and verify no crash */
    {
        const char *testfile = "test_minimal.chm";
        FILE *f = fopen(testfile, "wb");
        if (f == NULL) {
            printf("SKIP 2: cannot create test file\n");
        } else {
            /* Minimal ITSF v3 header — 96 bytes */
            unsigned char buf[96];
            memset(buf, 0, sizeof(buf));
            memcpy(buf, "ITSF", 4);
            buf[4]  = 3;       /* version LE = 3 */
            buf[8]  = 0x60;    /* header length LE = 96 */
            buf[12] = 1;       /* unknown, always 1 */
            size_t written = fwrite(buf, 1, sizeof(buf), f);
            int closed = fclose(f);
            if (written != sizeof(buf) || closed != 0) {
                printf("SKIP 2: failed to write/close test file (wrote %zu, close=%d)\n",
                       written, closed);
                remove(testfile);
                goto done;
            }

            h = chm_open(testfile);
            if (h != NULL) {
                chm_close(h);
                printf("PASS 2: chm_open succeeded on minimal ITSF file, closed safely\n");
            } else {
                printf("PASS 2: chm_open gracefully rejected incomplete ITSF file\n");
            }
            remove(testfile);
        }
    }
done:

    if (failures > 0) {
        fprintf(stderr, "\nchmlib test FAILED: %d check(s) failed\n", failures);
        return 1;
    }
    printf("\nchmlib test PASSED\n");
    return 0;
}
