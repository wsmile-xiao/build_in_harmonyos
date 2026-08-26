#include <parson.h>

#include <stdio.h>
#include <string.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        failures++; \
    } \
} while (0)

int main(void) {
    const char *document =
        "{\"name\":\"HarmonyOS\",\"version\":1.5,"
        "\"features\":{\"json\":true},\"items\":[1,2,3]}";
    JSON_Value *root = json_parse_string(document);
    JSON_Object *object;
    JSON_Value *schema;
    JSON_Value *copy;
    char *serialized;
    int failures = 0;

    CHECK(root != NULL, "parse a valid JSON document");
    object = json_value_get_object(root);
    CHECK(object != NULL, "obtain the root object");
    CHECK(strcmp(json_object_get_string(object, "name"), "HarmonyOS") == 0,
          "read a string member");
    CHECK(json_object_get_number(object, "version") == 1.5,
          "read a number member");
    CHECK(json_object_dotget_boolean(object, "features.json") == 1,
          "read a nested boolean with dot notation");
    CHECK(json_array_get_count(json_object_get_array(object, "items")) == 3,
          "read an array member");
    CHECK(json_object_dotset_string(object, "build.arch", "arm64") == JSONSuccess,
          "create nested members with dot notation");

    serialized = json_serialize_to_string(root);
    CHECK(serialized != NULL && strstr(serialized, "\"arch\":\"arm64\"") != NULL,
          "serialize the mutated document");

    schema = json_parse_string(
        "{\"name\":\"\",\"version\":0,\"features\":{\"json\":true},"
        "\"items\":[0],\"build\":{\"arch\":\"\"}}"
    );
    CHECK(json_validate(schema, root) == JSONSuccess,
          "validate the document against a schema");

    copy = json_value_deep_copy(root);
    CHECK(copy != NULL && json_value_equals(root, copy),
          "deep-copy preserves the JSON value");
    CHECK(json_parse_string("{invalid}") == NULL,
          "reject malformed JSON");

    json_value_free(copy);
    json_value_free(schema);
    json_free_serialized_string(serialized);
    json_value_free(root);

    if (failures != 0) {
        fprintf(stderr, "Parson consumer test failed: %d assertion(s)\n", failures);
        return 1;
    }
    puts("Parson consumer test passed: 11 assertions");
    return 0;
}
