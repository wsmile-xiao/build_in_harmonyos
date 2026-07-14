#include <stdio.h>
#include <stdlib.h>
#include "uuid.h"

int main(void) {
    uuid_t *u = NULL;
    uuid_rc_t rc;

    rc = uuid_create(&u);
    if (rc != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_create returned %d\n", (int)rc);
        return 1;
    }
    if (u == NULL) {
        fprintf(stderr, "FAIL: uuid_create returned NULL\n");
        return 1;
    }
    fprintf(stderr, "uuid_create OK\n");

    /* Make a UUID v1 (time-based) with default */
    rc = uuid_make(u, UUID_MAKE_V1);
    if (rc != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_make returned %d\n", (int)rc);
        uuid_destroy(u);
        return 1;
    }
    fprintf(stderr, "uuid_make OK\n");

    /* Export to string */
    char *str = NULL;
    size_t len = 0;
    rc = uuid_export(u, UUID_FMT_STR, &str, &len);
    if (rc != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_export returned %d\n", (int)rc);
        uuid_destroy(u);
        return 1;
    }
    if (str == NULL) {
        fprintf(stderr, "FAIL: uuid_export returned NULL\n");
        uuid_destroy(u);
        return 1;
    }

    fprintf(stderr, "uuid_export OK: %s (len=%zu)\n", str, len);
    free(str);
    uuid_destroy(u);
    printf("test ossp-uuid 1.6.2-r5: OK\n");
    return 0;
}