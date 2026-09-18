/*
 * libidl consumer test.
 *
 * Links against the installed libIDL-2 library and public headers only, and
 * drives the documented API surface: version query, parsing IDL from an
 * in-memory buffer (IDL_parse_filename_with_input, no external cpp needed),
 * tree walking/type inspection and re-serialisation with IDL_tree_to_IDL_string.
 */
#include <stdio.h>
#include <string.h>

#include <glib.h>
#include <libIDL/IDL.h>

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

static const char VALID_IDL[] =
    "module Demo {\n"
    "  interface Greeter {\n"
    "    attribute string name;\n"
    "    long add1(in long value);\n"
    "  };\n"
    "};\n";

typedef struct {
    const char *data;
    size_t size;
    size_t position;
} InputBuffer;

static int input_callback(IDL_input_reason reason,
                          union IDL_input_data *data,
                          gpointer user_data)
{
    InputBuffer *buffer = (InputBuffer *)user_data;

    switch (reason) {
    case IDL_INPUT_REASON_INIT:
        return 0;
    case IDL_INPUT_REASON_FILL: {
        size_t remaining = buffer->size - buffer->position;
        size_t count = data->fill.max_size < remaining ? data->fill.max_size : remaining;
        if (count == 0)
            return 0; /* EOF */
        memcpy(data->fill.buffer, buffer->data + buffer->position, count);
        buffer->position += count;
        return (int)count;
    }
    case IDL_INPUT_REASON_ABORT:
        return 0;
    case IDL_INPUT_REASON_FINISH:
        return 0;
    }
    return 0;
}

static gboolean count_nodes(IDL_tree_func_data *tnfd, gpointer user_data)
{
    int *counters = (int *)user_data;

    switch (IDL_NODE_TYPE(tnfd->tree)) {
    case IDLN_MODULE:
        counters[0]++;
        break;
    case IDLN_INTERFACE:
        counters[1]++;
        break;
    case IDLN_ATTR_DCL:
        counters[2]++;
        break;
    case IDLN_OP_DCL:
        counters[3]++;
        break;
    default:
        break;
    }
    return TRUE;
}

static int parse(const char *text, IDL_tree *tree, IDL_ns *ns)
{
    InputBuffer buffer;

    buffer.data = text;
    buffer.size = strlen(text);
    buffer.position = 0;
    return IDL_parse_filename_with_input("string.idl", input_callback, &buffer,
                                         NULL, tree, ns, 0, IDL_WARNING1);
}

/*
 * Upstream libIDL 0.8.14 crashes in its syntax-error recovery path, so the
 * negative case is expressed as "input cannot be read at all" (the callback
 * refuses on INIT), which the library reports cleanly.
 */
static int failing_input_callback(IDL_input_reason reason,
                                  union IDL_input_data *data,
                                  gpointer user_data)
{
    (void)data;
    (void)user_data;
    if (reason == IDL_INPUT_REASON_INIT)
        return -1;
    return 0;
}

int main(void)
{
    int failures = 0;
    const char *version = IDL_get_libver_string();

    printf("libidl consumer test\n");

    /* --- version ------------------------------------------------------ */
    CHECK(version != NULL, "IDL_get_libver_string returns a value");
    CHECK(version != NULL && strncmp(version, "0.8", 3) == 0,
          "reported version is the 0.8 series");

    /* --- parse a valid IDL document ----------------------------------- */
    {
        IDL_tree tree = NULL;
        IDL_ns ns = NULL;
        int result = parse(VALID_IDL, &tree, &ns);

        CHECK(result == IDL_SUCCESS, "IDL_parse_filename_with_input succeeds");
        CHECK(tree != NULL, "parser returns a syntax tree");
        CHECK(ns != NULL, "parser returns a namespace");

        if (tree != NULL && ns != NULL) {
            int counters[4] = { 0, 0, 0, 0 };
            GString *text;
            IDL_tree_walk_in_order(tree, count_nodes, counters);
            printf("  info modules=%d interfaces=%d attributes=%d operations=%d\n",
                   counters[0], counters[1], counters[2], counters[3]);
            CHECK(counters[0] == 1, "tree contains exactly one module");
            CHECK(counters[1] == 1, "tree contains exactly one interface");
            CHECK(counters[2] == 1, "interface declares exactly one attribute");
            CHECK(counters[3] == 1, "interface declares exactly one operation");
            text = IDL_tree_to_IDL_string(tree, ns, 0);
            CHECK(text != NULL && text->len > 0, "IDL_tree_to_IDL_string re-serialises the tree");
            if (text != NULL) {
                printf("  info serialised IDL: %u bytes\n", (unsigned)text->len);
                CHECK(strstr(text->str, "interface Greeter") != NULL,
                      "re-serialised IDL keeps the interface name");
                CHECK(strstr(text->str, "add1") != NULL,
                      "re-serialised IDL keeps the operation name");
                CHECK(strstr(text->str, "string") != NULL,
                      "re-serialised IDL keeps the attribute type");
                g_string_free(text, TRUE);
            }
            IDL_ns_free(ns);
            IDL_tree_free(tree);
        }
    }

    /* --- an unreadable input must be reported, not accepted ----------- */
    {
        IDL_tree tree = NULL;
        IDL_ns ns = NULL;
        int result = IDL_parse_filename_with_input("missing.idl", failing_input_callback,
                                                   NULL, NULL, &tree, &ns, 0, IDL_WARNING1);

        printf("  info unreadable input result=%d\n", result);
        CHECK(result != IDL_SUCCESS, "an unreadable input is reported as an error");
        if (tree != NULL)
            IDL_tree_free(tree);
        if (ns != NULL)
            IDL_ns_free(ns);
    }

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
