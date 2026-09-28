#include <json-glib/json-glib.h>
#include <stdio.h>

int main(void) {
    /* Initialize the type system */
    g_type_init();

    /* Parse a simple JSON string */
    GError *error = NULL;
    JsonParser *parser = json_parser_new();
    const char *json_data = "{\"name\":\"test\",\"value\":42}";

    if (!json_parser_load_from_data(parser, json_data, -1, &error)) {
        fprintf(stderr, "FAIL: json_parser_load_from_data failed: %s\n", error->message);
        g_error_free(error);
        g_object_unref(parser);
        return 1;
    }

    /* Get the root node */
    JsonNode *root = json_parser_get_root(parser);
    if (!root) {
        fprintf(stderr, "FAIL: json_parser_get_root returned NULL\n");
        g_object_unref(parser);
        return 1;
    }

    /* Navigate to the object */
    JsonObject *object = json_node_get_object(root);
    if (!object) {
        fprintf(stderr, "FAIL: json_node_get_object returned NULL\n");
        g_object_unref(parser);
        return 1;
    }

    /* Check the string member */
    const gchar *name = json_object_get_string_member(object, "name");
    if (!name || g_strcmp0(name, "test") != 0) {
        fprintf(stderr, "FAIL: name='%s' (expected 'test')\n", name ? name : "(null)");
        g_object_unref(parser);
        return 1;
    }

    /* Check the integer member */
    gint value = json_object_get_int_member(object, "value");
    if (value != 42) {
        fprintf(stderr, "FAIL: value=%d (expected 42)\n", value);
        g_object_unref(parser);
        return 1;
    }

    printf("test json-glib 1.10.6.1: OK (name=%s, value=%d)\n", name, value);
    g_object_unref(parser);
    return 0;
}
