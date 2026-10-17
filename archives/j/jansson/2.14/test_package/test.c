/* test_package for jansson 2.14 — API round-trip verification.
 *
 * 构造 → 序列化 → 解析 → 校验 → 释放 往返验证：
 * json_object / json_string / json_integer / json_dumps / json_loads /
 * json_object_get / json_is_string / json_is_integer / json_string_value /
 * json_integer_value / json_array / json_decref
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <jansson.h>

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void) {
    /* --- 构造 JSON 对象 --- */
    json_t *root = json_object();
    CHECK(root != NULL, "json_object() returned NULL");

    int r = json_object_set_new(root, "name", json_string("jansson"));
    CHECK(r == 0, "json_object_set_new(name) failed");

    r = json_object_set_new(root, "version", json_string("2.14"));
    CHECK(r == 0, "json_object_set_new(version) failed");

    r = json_object_set_new(root, "tests", json_integer(213));
    CHECK(r == 0, "json_object_set_new(tests) failed");

    /* --- 数组 --- */
    json_t *arr = json_array();
    CHECK(arr != NULL, "json_array() returned NULL");
    r = json_array_append_new(arr, json_integer(1));
    CHECK(r == 0, "json_array_append_new(1) failed");
    r = json_array_append_new(arr, json_integer(2));
    CHECK(r == 0, "json_array_append_new(2) failed");
    r = json_object_set_new(root, "list", arr);
    CHECK(r == 0, "json_object_set_new(list) failed");

    /* --- 序列化 --- */
    char *str = json_dumps(root, JSON_COMPACT);
    CHECK(str != NULL, "json_dumps() returned NULL");

    /* --- 解析回来（往返验证） --- */
    json_error_t error;
    json_t *parsed = json_loads(str, 0, &error);
    CHECK(parsed != NULL, "json_loads() failed");
    if (!parsed) {
        fprintf(stderr, "  json error: %s (line %d)\n", error.text, error.line);
    }

    if (parsed) {
        json_t *name = json_object_get(parsed, "name");
        CHECK(name != NULL && json_is_string(name), "name is not a string");
        CHECK(name && strcmp(json_string_value(name), "jansson") == 0,
              "name value mismatch");

        json_t *ver = json_object_get(parsed, "version");
        CHECK(ver != NULL && json_is_string(ver), "version is not a string");
        CHECK(ver && strcmp(json_string_value(ver), "2.14") == 0,
              "version value mismatch");

        json_t *tests = json_object_get(parsed, "tests");
        CHECK(tests != NULL && json_is_integer(tests), "tests is not an integer");
        CHECK(tests && json_integer_value(tests) == 213, "tests value mismatch");

        json_t *list = json_object_get(parsed, "list");
        CHECK(list != NULL && json_is_array(list), "list is not an array");
        CHECK(list && json_array_size(list) == 2, "list size mismatch");
        CHECK(list && json_integer_value(json_array_get(list, 0)) == 1,
              "list[0] value mismatch");
        CHECK(list && json_integer_value(json_array_get(list, 1)) == 2,
              "list[1] value mismatch");

        json_decref(parsed);
    }

    free(str);
    json_decref(root);

    if (failures > 0) {
        fprintf(stderr, "test_jansson: %d assertion(s) failed\n", failures);
        return 1;
    }

    printf("test_jansson 2.14: all round-trip assertions passed\n");
    return 0;
}
