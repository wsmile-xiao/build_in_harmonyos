/*
 * Consumer test for libproperties 1.1.2.
 *
 * Links against the *installed* package (CMakeDeps imported target) and drives
 * the public API declared in properties.h, so it also fingerprints the shipped
 * header: it cannot compile without properties_source_string_read /
 * struct properties_source_string_t and cannot link without libproperties.
 */
#include <stdio.h>
#include <string.h>

#include "properties.h"

static int g_entries;
static int g_greeting_seen;

static int on_entry(void* context, char* key, int key_len, char* val, int val_len)
{
    char entry[256];

    (void)context;
    if (key_len < 0 || val_len < 0 || key_len + val_len >= (int)sizeof(entry) - 2) {
        return -1;
    }
    memcpy(entry, key, (size_t)key_len);
    entry[key_len] = '=';
    memcpy(entry + key_len + 1, val, (size_t)val_len);
    entry[key_len + 1 + val_len] = '\0';

    g_entries++;
    if (strcmp(entry, "greeting=hello ohos") == 0) {
        g_greeting_seen = 1;
    }
    return 0;
}

int main(void)
{
    /* '#'/'!' leading lines are comments and must produce no entry. */
    char text[] = "! leading comment\n"
                  "# hash comment\n"
                  "greeting=hello ohos\n"
                  "port=8080\n"
                  "empty=\n";
    struct properties_source_string_t source;
    int rc;

    source.str = text;
    source.end = text + strlen(text);

    rc = properties_parse(&source, properties_source_string_read, NULL, on_entry);
    if (rc != 0) {
        fprintf(stderr, "test_libproperties_api: FAIL — properties_parse rc=%d\n", rc);
        return 1;
    }
    if (g_entries != 3) {
        fprintf(stderr, "test_libproperties_api: FAIL — expected 3 entries, got %d\n", g_entries);
        return 1;
    }
    if (!g_greeting_seen) {
        fprintf(stderr, "test_libproperties_api: FAIL — 'greeting=hello ohos' not reported\n");
        return 1;
    }

    printf("test_libproperties_api: OK (3 entries parsed, greeting matched)\n");
    return 0;
}
