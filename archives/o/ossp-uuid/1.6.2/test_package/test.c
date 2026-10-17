#include <uuid.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    uuid_t *uuid;
    char *str = NULL;
    size_t len = 0;

    /* Test: create a UUID object */
    if (uuid_create(&uuid) != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_create failed\n");
        return 1;
    }

    /* Test: generate a v4 (random) UUID */
    if (uuid_make(uuid, UUID_MAKE_V4) != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_make failed\n");
        uuid_destroy(uuid);
        return 1;
    }

    /* Test: export UUID as string */
    if (uuid_export(uuid, UUID_FMT_STR, (void **)&str, &len) != UUID_RC_OK) {
        fprintf(stderr, "FAIL: uuid_export failed\n");
        uuid_destroy(uuid);
        return 1;
    }

    /* Verify: UUID string should be 36 chars + null terminator = 37 bytes */
    if (str == NULL || len < 37) {
        fprintf(stderr, "FAIL: invalid UUID length %zu\n", len);
        free(str);
        uuid_destroy(uuid);
        return 1;
    }

    printf("OK: ossp-uuid 1.6.2 test passed, UUID: %s\n", str);
    free(str);
    uuid_destroy(uuid);
    return 0;
}
