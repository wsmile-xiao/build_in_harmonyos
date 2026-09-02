/*
 * test_package consumer test for libcbor 0.10.2 on HarmonyOS PC (aarch64-linux-ohos).
 *
 * Actually exercises the packaged libcbor public API (R34): encode an integer
 * and a string to CBOR bytes, decode them back, and verify round-trip values.
 *
 * NOTE: uses CHECK() instead of assert() so the validation still runs under
 * Release (-DNDEBUG) builds — assert() is compiled out by NDEBUG, which would
 * otherwise make the test validate nothing in CI.
 */
#include <stdio.h>
#include <string.h>
#include "cbor.h"

#define CHECK(expr)                                                     \
    do {                                                                \
        if (!(expr)) {                                                  \
            fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__,     \
                    #expr);                                             \
            return 1;                                                   \
        }                                                               \
    } while (0)

static int test_uint_roundtrip(void) {
    unsigned char buf[16];
    cbor_item_t *item = cbor_build_uint8(42);
    CHECK(item != NULL);
    size_t len = cbor_serialize_uint(item, buf, sizeof(buf));
    CHECK(len == 2); /* 42 in uint8: 0x18 0x2A */
    CHECK(buf[0] == 0x18);
    CHECK(buf[1] == 0x2A);
    cbor_decref(&item);

    struct cbor_load_result res;
    cbor_item_t *decoded = cbor_load(buf, len, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_typeof(decoded) == CBOR_TYPE_UINT);
    CHECK(cbor_get_int(decoded) == 42);
    cbor_decref(&decoded);
    return 0;
}

static int test_string_roundtrip(void) {
    const char *s = "HarmonyOS libcbor";
    cbor_item_t *item = cbor_build_string(s);
    CHECK(item != NULL);

    size_t cap = cbor_serialized_size(item);
    unsigned char *buf = malloc(cap);
    CHECK(buf != NULL);
    size_t len = cbor_serialize(item, buf, cap);
    CHECK(len == cap);
    cbor_decref(&item);

    struct cbor_load_result res;
    cbor_item_t *decoded = cbor_load(buf, len, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_typeof(decoded) == CBOR_TYPE_STRING);
    CHECK(cbor_string_length(decoded) == strlen(s));
    CHECK(memcmp(cbor_string_handle(decoded), s, strlen(s)) == 0);
    cbor_decref(&decoded);
    free(buf);
    return 0;
}

static int test_array_roundtrip(void) {
    cbor_item_t *root = cbor_new_definite_array(2);
    cbor_array_push(root, cbor_move(cbor_build_uint64(1)));
    cbor_array_push(root, cbor_move(cbor_build_uint64(2)));

    size_t cap = cbor_serialized_size(root);
    unsigned char *buf = malloc(cap);
    CHECK(buf != NULL);
    size_t len = cbor_serialize(root, buf, cap);
    CHECK(len == cap);
    cbor_decref(&root);

    struct cbor_load_result res;
    cbor_item_t *decoded = cbor_load(buf, len, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_typeof(decoded) == CBOR_TYPE_ARRAY);
    CHECK(cbor_array_size(decoded) == 2);
    CHECK(cbor_get_int(cbor_array_get(decoded, 0)) == 1);
    CHECK(cbor_get_int(cbor_array_get(decoded, 1)) == 2);
    cbor_decref(&decoded);
    free(buf);
    return 0;
}

int main(void) {
    printf("libcbor consumer test start (version %s)\n", CBOR_VERSION);
    if (test_uint_roundtrip() != 0) return 1;
    if (test_string_roundtrip() != 0) return 1;
    if (test_array_roundtrip() != 0) return 1;
    printf("libcbor 0.10.2 consumer test: ALL PASSED\n");
    return 0;
}
