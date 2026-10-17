#include "mpack.h"

#include <stdio.h>
#include <stdlib.h>

int main(void) {
    /* ── Encode: {"compact": true, "schema": 42} ── */
    char *data = NULL;
    size_t size = 0;
    mpack_writer_t writer;
    mpack_writer_init_growable(&writer, &data, &size);

    mpack_build_map(&writer);
    mpack_write_cstr(&writer, "compact");
    mpack_write_bool(&writer, true);
    mpack_write_cstr(&writer, "schema");
    mpack_write_uint(&writer, 42);
    mpack_complete_map(&writer);

    if (mpack_writer_destroy(&writer) != mpack_ok) {
        fprintf(stderr, "Failed to encode data\n");
        if (data) free(data);
        return 1;
    }

    /* ── Decode: parse the encoded data back into a tree ── */
    mpack_tree_t tree;
    mpack_tree_init_data(&tree, data, size);
    mpack_tree_parse(&tree);
    mpack_error_t error = mpack_tree_error(&tree);
    if (error != mpack_ok) {
        fprintf(stderr, "Failed to parse MessagePack data (error %d)\n", (int)error);
        mpack_tree_destroy(&tree);
        free(data);
        return 1;
    }
    mpack_node_t root = mpack_tree_root(&tree);

    bool compact = mpack_node_bool(mpack_node_map_cstr(root, "compact"));
    int schema = (int)mpack_node_i32(mpack_node_map_cstr(root, "schema"));

    mpack_tree_destroy(&tree);
    free(data);

    /* ── Verify ── */
    int errors = 0;
    if (!compact) {
        fprintf(stderr, "FAIL: compact expected true, got false\n");
        errors++;
    }
    if (schema != 42) {
        fprintf(stderr, "FAIL: schema expected 42, got %d\n", schema);
        errors++;
    }

    if (errors > 0) {
        fprintf(stderr, "test_mpack: %d assertion(s) failed\n", errors);
        return 1;
    }

    printf("test_mpack: OK (encode + decode round-trip, compact=true schema=42)\n");
    return 0;
}
