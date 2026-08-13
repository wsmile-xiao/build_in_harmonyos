#include <string.h>

#include <json-glib/json-glib.h>

int main(void)
{
    const char *payload = "{\"name\":\"openharmony\",\"count\":3,\"items\":[1,2,3]}";
    g_autoptr(GError) error = NULL;
    JsonParser *parser = json_parser_new();

    if (!json_parser_load_from_data(parser, payload, -1, &error)) {
        g_object_unref(parser);
        return 1;
    }

    JsonNode *root = json_parser_get_root(parser);
    if (root == NULL || json_node_get_node_type(root) != JSON_NODE_OBJECT) {
        g_object_unref(parser);
        return 2;
    }

    JsonObject *object = json_node_get_object(root);
    if (!json_object_has_member(object, "name") ||
        strcmp(json_object_get_string_member(object, "name"), "openharmony") != 0) {
        g_object_unref(parser);
        return 3;
    }

    if (json_object_get_int_member(object, "count") != 3) {
        g_object_unref(parser);
        return 4;
    }

    JsonReader *reader = json_reader_new(root);
    if (!json_reader_read_member(reader, "items")) {
        g_object_unref(reader);
        g_object_unref(parser);
        return 5;
    }

    if (json_reader_count_elements(reader) != 3) {
        g_object_unref(reader);
        g_object_unref(parser);
        return 6;
    }

    json_reader_end_member(reader);
    g_object_unref(reader);
    g_object_unref(parser);
    return 0;
}
