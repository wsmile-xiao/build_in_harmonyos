#include <stdio.h>
#include <string.h>

#include <cpluff.h>

int main(void) {
    int failures = 0;

    if (cp_init() != CP_OK) {
        fprintf(stderr, "FAIL: cp_init did not return CP_OK\n");
        return 1;
    }
    printf("PASS: cp_init returned CP_OK\n");

    {
        const char *ver = cp_get_version();
        if (ver == NULL || ver[0] == '\0') {
            fprintf(stderr, "FAIL: cp_get_version returned empty\n");
        } else {
            printf("PASS: cpluff version: %s\n", ver);
            if (strstr(ver, "0.2.0") == NULL) {
                fprintf(stderr, "FAIL: version does not contain 0.2.0: %s\n", ver);
                failures++;
            } else {
                printf("PASS: version contains 0.2.0\n");
            }
        }
        if (ver == NULL || ver[0] == '\0') {
            failures++;
        }
    }

    {
        cp_status_t status = CP_OK;
        cp_context_t *ctx = cp_create_context(&status);
        if (ctx == NULL || status != CP_OK) {
            fprintf(stderr, "FAIL: cp_create_context failed status=%d ctx=%p\n", (int)status, (void *)ctx);
            failures++;
        } else {
            printf("PASS: cp_create_context succeeded\n");
            cp_destroy_context(ctx);
            printf("PASS: cp_destroy_context succeeded\n");
        }
    }

    cp_destroy();

    if (failures != 0) {
        fprintf(stderr, "FAIL: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test cpluff 0.2.0: OK\n");
    return 0;
}
