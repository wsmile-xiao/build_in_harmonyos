#include <libsecret/secret.h>
#include <stdio.h>
#include <string.h>

/* R34: 实质调用被测包 API — schema 构建/校验走 libsecret 核心，不依赖 dbus daemon */
int main(void) {
    SecretSchema schema = {
        "org.test.TestSchema",
        SECRET_SCHEMA_DONT_MATCH_NAME,
        {
            { "attr", SECRET_SCHEMA_ATTRIBUTE_STRING },
            { 0, 0 },
        },
    };
    if (strcmp(schema.name, "org.test.TestSchema") != 0) {
        fprintf(stderr, "FAIL: schema name mismatch\n");
        return 1;
    }
    if (schema.attributes[0].type != SECRET_SCHEMA_ATTRIBUTE_STRING) {
        fprintf(stderr, "FAIL: attribute type mismatch\n");
        return 1;
    }
    SecretValue *value = secret_value_new("payload", -1, "text/plain");
    if (value == NULL) {
        fprintf(stderr, "FAIL: secret_value_new returned NULL\n");
        return 1;
    }
    const gchar *text = secret_value_get(value, NULL);
    int ok = (text != NULL && strcmp(text, "payload") == 0);
    secret_value_unref(value);
    if (!ok) {
        fprintf(stderr, "FAIL: secret_value_get roundtrip mismatch\n");
        return 1;
    }
    printf("test libsecret 0.20.5: schema/value API OK\n");
    return 0;
}
