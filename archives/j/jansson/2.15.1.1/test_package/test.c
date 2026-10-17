#include <stdio.h>
#include <stdlib.h>
#include <jansson.h>

int main(void) {
    /* Build a JSON object */
    json_t *root = json_object();
    if (!root) {
        fprintf(stderr, "json_object failed\n");
        return 1;
    }
    json_object_set_new(root, "name", json_string("jansson"));
    json_object_set_new(root, "version", json_string("2.15.1"));
    json_object_set_new(root, "tests", json_integer(215));

    /* Serialize to string */
    char *str = json_dumps(root, JSON_INDENT(2));
    if (!str) {
        fprintf(stderr, "json_dumps failed\n");
        json_decref(root);
        return 1;
    }

    printf("Encoded JSON:\n%s\n", str);
    free(str);

    /* Parse it back */
    json_error_t error;
    json_t *parsed = json_loads("{\"key\":\"value\",\"num\":42}", 0, &error);
    if (!parsed) {
        fprintf(stderr, "json_loads failed: %s\n", error.text);
        json_decref(root);
        return 1;
    }

    /* Verify parsed values */
    json_t *key = json_object_get(parsed, "key");
    json_t *num = json_object_get(parsed, "num");
    if (!json_is_string(key) || !json_is_integer(num)) {
        fprintf(stderr, "parsed values incorrect\n");
        json_decref(root);
        json_decref(parsed);
        return 1;
    }

    if (json_integer_value(num) != 42) {
        fprintf(stderr, "integer value mismatch\n");
        json_decref(root);
        json_decref(parsed);
        return 1;
    }

    printf("Parsed key: %s, num: %lld\n",
           json_string_value(key),
           (long long)json_integer_value(num));

    json_decref(root);
    json_decref(parsed);

    printf("test jansson 2.15.1: OK\n");
    return 0;
}
