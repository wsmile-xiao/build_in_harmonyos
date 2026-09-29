#include <json-glib/json-glib.h>
#include <stdio.h>
#include <string.h>

static int fail(const char *message) {
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

int main(void) {
    const gchar *input =
        "{\"name\":\"harmony\",\"value\":42,\"enabled\":true," 
        "\"items\":[1,2,3]}";
    GError *error = NULL;
    JsonParser *parser = json_parser_new();

    if (!json_parser_load_from_data(parser, input, -1, &error)) {
        fprintf(stderr, "FAIL: parse: %s\n", error ? error->message : "unknown");
        g_clear_error(&error);
        g_object_unref(parser);
        return 1;
    }

    JsonNode *root = json_parser_get_root(parser);
    if (!root || !JSON_NODE_HOLDS_OBJECT(root)) {
        g_object_unref(parser);
        return fail("root is not an object");
    }

    JsonObject *object = json_node_get_object(root);
    if (g_strcmp0(json_object_get_string_member(object, "name"), "harmony") != 0) {
        g_object_unref(parser);
        return fail("string member mismatch");
    }
    if (json_object_get_int_member(object, "value") != 42) {
        g_object_unref(parser);
        return fail("integer member mismatch");
    }
    if (!json_object_get_boolean_member(object, "enabled")) {
        g_object_unref(parser);
        return fail("boolean member mismatch");
    }

    JsonArray *items = json_object_get_array_member(object, "items");
    if (!items || json_array_get_length(items) != 3 ||
        json_array_get_int_element(items, 2) != 3) {
        g_object_unref(parser);
        return fail("array member mismatch");
    }

    JsonPath *path = json_path_new();
    if (!json_path_compile(path, "$.items[1]", &error)) {
        fprintf(stderr, "FAIL: path compile: %s\n", error ? error->message : "unknown");
        g_clear_error(&error);
        g_object_unref(path);
        g_object_unref(parser);
        return 1;
    }
    JsonNode *match = json_path_match(path, root);
    if (!match || !JSON_NODE_HOLDS_ARRAY(match) ||
        json_array_get_int_element(json_node_get_array(match), 0) != 2) {
        if (match)
            json_node_unref(match);
        g_object_unref(path);
        g_object_unref(parser);
        return fail("JSONPath result mismatch");
    }

    JsonGenerator *generator = json_generator_new();
    json_generator_set_root(generator, root);
    gchar *output = json_generator_to_data(generator, NULL);
    if (!output || strstr(output, "\"harmony\"") == NULL) {
        g_free(output);
        g_object_unref(generator);
        json_node_unref(match);
        g_object_unref(path);
        g_object_unref(parser);
        return fail("generator output mismatch");
    }

    printf("json-glib consumer PASS: value=42 path=2 items=3\n");
    g_free(output);
    g_object_unref(generator);
    json_node_unref(match);
    g_object_unref(path);
    g_object_unref(parser);
    return 0;
}
