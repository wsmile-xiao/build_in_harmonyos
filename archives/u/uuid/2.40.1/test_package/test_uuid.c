#include <stdio.h>
#include <string.h>
#include <uuid/uuid.h>

int main(void) {
    uuid_t generated;
    uuid_t parsed;
    char text[37];

    uuid_generate(generated);
    uuid_unparse_lower(generated, text);

    if (strlen(text) != 36) {
        fprintf(stderr, "uuid text length mismatch: %zu\n", strlen(text));
        return 1;
    }

    if (uuid_parse(text, parsed) != 0) {
        fprintf(stderr, "uuid_parse failed for %s\n", text);
        return 1;
    }

    if (uuid_compare(generated, parsed) != 0) {
        fprintf(stderr, "parsed uuid does not match generated uuid\n");
        return 1;
    }

    uuid_clear(parsed);
    if (!uuid_is_null(parsed)) {
        fprintf(stderr, "uuid_clear did not produce a null uuid\n");
        return 1;
    }

    printf("PASS: libuuid generated, parsed, compared, and cleared a UUID\n");
    return 0;
}
