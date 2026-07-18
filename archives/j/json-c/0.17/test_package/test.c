#include <stdio.h>
#include <json-c/json.h>
int main(void) {
    struct json_object *obj = json_object_new_object();
    if (!obj) {
        fprintf(stderr, "FAIL: json_object_new_object returned NULL\n");
        return 1;
    }
    json_object_object_add(obj, "test", json_object_new_string("ok"));
    const char *str = json_object_to_json_string(obj);
    if (!str) {
        fprintf(stderr, "FAIL: json_object_to_json_string returned NULL\n");
        json_object_put(obj);
        return 1;
    }
    printf("json-c: %s\n", str);
    json_object_put(obj);
    return 0;
}
