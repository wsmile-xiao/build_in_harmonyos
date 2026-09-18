#include <stdio.h>
#include <string.h>
#include <uuid/uuid.h>

int main(void) {
    uuid_t uuid, uuid2;
    char str[37];

    /* Generate a random UUID */
    uuid_generate(uuid);
    uuid_unparse_lower(uuid, str);
    printf("Generated UUID: %s\n", str);

    /* Parse it back */
    if (uuid_parse(str, uuid2) != 0) {
        fprintf(stderr, "uuid_parse failed\n");
        return 1;
    }

    /* Compare */
    if (uuid_compare(uuid, uuid2) != 0) {
        fprintf(stderr, "uuid_compare failed\n");
        return 1;
    }

    /* is_null / clear */
    if (uuid_is_null(uuid)) {
        fprintf(stderr, "uuid_is_null: expected non-null\n");
        return 1;
    }
    uuid_clear(uuid);
    if (!uuid_is_null(uuid)) {
        fprintf(stderr, "uuid_is_null: expected null after clear\n");
        return 1;
    }

    printf("All UUID tests passed!\n");
    return 0;
}