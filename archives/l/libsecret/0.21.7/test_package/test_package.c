#include <libsecret/secret.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    int failures = 0;

    /* 1. Version macros match the adapted release */
    if (SECRET_MAJOR_VERSION != 0 || SECRET_MINOR_VERSION != 21 ||
        SECRET_MICRO_VERSION != 7) {
        fprintf(stderr, "FAIL: version %d.%d.%d (expected 0.21.7)\n",
                SECRET_MAJOR_VERSION, SECRET_MINOR_VERSION, SECRET_MICRO_VERSION);
        failures++;
    }

    /* 2. Schema build/validate API (pure in-memory) */
    static const SecretSchema MOCK_SCHEMA = {
        "org.mock.Schema",
        SECRET_SCHEMA_DONT_MATCH_NAME,
        {
            { "number", SECRET_SCHEMA_ATTRIBUTE_INTEGER },
            { "string", SECRET_SCHEMA_ATTRIBUTE_STRING },
            { "even",   SECRET_SCHEMA_ATTRIBUTE_BOOLEAN },
            { NULL,     0 },
        }
    };
    GHashTable *attrs = secret_attributes_build(&MOCK_SCHEMA,
                                                "number", 4,
                                                "string", "four",
                                                "even", TRUE,
                                                NULL);
    if (attrs == NULL) {
        fprintf(stderr, "FAIL: secret_attributes_build returned NULL\n");
        failures++;
    } else {
        if (g_strcmp0(g_hash_table_lookup(attrs, "number"), "4") != 0) {
            fprintf(stderr, "FAIL: number attribute mismatch\n");
            failures++;
        }
        if (g_strcmp0(g_hash_table_lookup(attrs, "string"), "four") != 0) {
            fprintf(stderr, "FAIL: string attribute mismatch\n");
            failures++;
        }
        if (g_strcmp0(g_hash_table_lookup(attrs, "even"), "true") != 0) {
            fprintf(stderr, "FAIL: boolean attribute mismatch\n");
            failures++;
        }
        g_hash_table_unref(attrs);
    }

    /* 3. SecretValue create/read/wipe lifecycle */
    SecretValue *value = secret_value_new("s3cr3t", -1, "text/plain");
    const gchar *text = secret_value_get_text(value);
    if (g_strcmp0(text, "s3cr3t") != 0) {
        fprintf(stderr, "FAIL: secret_value_get_text mismatch\n");
        failures++;
    }
    gsize len = 0;
    const gchar *raw = secret_value_get(value, &len);
    if (raw == NULL || len != 6 || memcmp(raw, "s3cr3t", 6) != 0) {
        fprintf(stderr, "FAIL: secret_value_get len=%zu (expected 6)\n", (gsize)len);
        failures++;
    }
    const gchar *ctype = secret_value_get_content_type(value);
    if (g_strcmp0(ctype, "text/plain") != 0) {
        fprintf(stderr, "FAIL: content type mismatch: %s\n", ctype ? ctype : "()");
        failures++;
    }
    secret_value_unref(value);

    /* 4. Well-known schemas are exported */
    if (SECRET_SCHEMA_NOTE == NULL) {
        fprintf(stderr, "FAIL: SECRET_SCHEMA_NOTE missing\n");
        failures++;
    }

    if (failures == 0) {
        printf("libsecret consumer test: PASS (version/schema/value APIs)\n");
        return 0;
    }
    fprintf(stderr, "libsecret consumer test: %d FAILURES\n", failures);
    return 1;
}
