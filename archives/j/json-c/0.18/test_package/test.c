#include <stdio.h>
#include <stdlib.h>
#include <json-c/json.h>

int main(void) {
    struct json_object *root = json_object_new_object();
    if (!root) {
        fprintf(stderr, "FAIL: json_object_new_object returned NULL\n");
        return 1;
    }

    json_object_object_add(root, "name", json_object_new_string("OpenHarmony"));
    json_object_object_add(root, "version", json_object_new_int(18));

    const char *str = json_object_to_json_string(root);
    if (!str) {
        fprintf(stderr, "FAIL: json_object_to_json_string returned NULL\n");
        json_object_put(root);
        return 1;
    }

    printf("JSON output: %s\n", str);

    struct json_object *parsed = json_tokener_parse(str);
    if (!parsed) {
        fprintf(stderr, "FAIL: json_tokener_parse failed\n");
        json_object_put(root);
        return 1;
    }

    struct json_object *name_obj = NULL;
    if (!json_object_object_get_ex(parsed, "name", &name_obj)) {
        fprintf(stderr, "FAIL: key 'name' not found\n");
        json_object_put(root);
        json_object_put(parsed);
        return 1;
    }

    const char *name_str = json_object_get_string(name_obj);
    printf("Parsed name: %s\n", name_str);

    json_object_put(root);
    json_object_put(parsed);

    printf("test json-c 0.18: PASS\n");
    return 0;
}
