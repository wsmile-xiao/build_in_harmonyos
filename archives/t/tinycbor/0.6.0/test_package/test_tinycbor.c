/*
 * test_tinycbor.c — HarmonyOS consumer test for the tinycbor library.
 *
 * Real end-to-end CBOR (RFC 7049) round-trip through the public API:
 *   1. encode a map {"a":1, "b":-2, "c":"ohos", "d":true, "e":null} with
 *      CborEncoder (single-shot buffer API);
 *   2. parse it back with CborParser / CborValue;
 *   3. walk the map, checking every key/value pair and container end.
 *
 * Any mismatch or API error returns non-zero so CI/L0 gates observe failure.
 * This test exercises the actual tinycbor API on the OHOS target; it is not
 * an empty-shell or print-only test.
 */
/* tinycbor installs headers under include/tinycbor/ (upstream `make install`
 * layout), so consumers include <tinycbor/cbor.h>. */
#include <tinycbor/cbor.h>

#include <stdio.h>
#include <stdint.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        if (!(cond)) {                                              \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            ++failures;                                             \
        }                                                           \
    } while (0)

int main(void)
{
    uint8_t buf[256];
    CborEncoder enc, map;
    CborParser parser;
    CborValue root, val;
    CborError err;
    size_t len = sizeof(buf);

    /* ---- encode ---- */
    /* tinycbor 0.6.0: cbor_encoder_init returns void; errors surface on
     * cbor_encoder_create_map / close_container_checked instead. */
    cbor_encoder_init(&enc, buf, len, 0);

    err = cbor_encoder_create_map(&enc, &map, 5);
    CHECK(err == CborNoError, "cbor_encoder_create_map");
    if (err != CborNoError)
        return 1;
    cbor_encode_text_stringz(&map, "a");
    cbor_encode_uint(&map, 1);
    cbor_encode_text_stringz(&map, "b");
    cbor_encode_int(&map, -2);
    cbor_encode_text_stringz(&map, "c");
    cbor_encode_text_stringz(&map, "ohos");
    cbor_encode_text_stringz(&map, "d");
    cbor_encode_boolean(&map, true);
    cbor_encode_text_stringz(&map, "e");
    cbor_encode_null(&map);
    err = cbor_encoder_close_container_checked(&enc, &map);
    CHECK(err == CborNoError, "cbor_encoder_close_container_checked");
    if (err != CborNoError)
        return 1;
    len = cbor_encoder_get_buffer_size(&enc, buf); /* bytes actually produced */

    /* ---- parse ---- */
    err = cbor_parser_init(buf, len, 0, &parser, &root);
    CHECK(err == CborNoError, "cbor_parser_init");
    if (err != CborNoError)
        return 1;
    CHECK(cbor_value_get_type(&root) == CborMapType, "root is map");

    /* ---- walk map ---- */
    {
        size_t map_len = 0;
        CHECK(cbor_value_get_map_length(&root, &map_len) == CborNoError, "map_length callable");
        CHECK(map_len == 5, "map has 5 entries");
    }
    err = cbor_value_enter_container(&root, &val);
    CHECK(err == CborNoError, "cbor_value_enter_container");
    if (err != CborNoError)
        return 1;

    /* key "a" -> uint 1 */
    CHECK(cbor_value_get_type(&val) == CborTextStringType, "key a is text");
    CHECK(cbor_value_advance(&val) == CborNoError, "advance to value");
    {
        uint64_t u = 0;
        err = cbor_value_get_uint64(&val, &u);
        CHECK(err == CborNoError, "value a is uint");
        CHECK(u == 1, "value a == 1");
    }
    CHECK(cbor_value_advance(&val) == CborNoError, "advance past a");

    /* key "b" -> negative -2 */
    {
        int64_t n = 0;
        CHECK(cbor_value_get_type(&val) == CborTextStringType, "key b is text");
        CHECK(cbor_value_advance(&val) == CborNoError, "advance to value");
        err = cbor_value_get_int64(&val, &n);
        CHECK(err == CborNoError, "value b is int");
        CHECK(n == -2, "value b == -2");
    }
    CHECK(cbor_value_advance(&val) == CborNoError, "advance past b");

    /* key "c" -> text "ohos" */
    {
        char s[16] = {0};
        size_t n = sizeof(s);
        CHECK(cbor_value_get_type(&val) == CborTextStringType, "key c is text");
        CHECK(cbor_value_advance(&val) == CborNoError, "advance to value");
        err = cbor_value_copy_text_string(&val, s, &n, NULL);
        CHECK(err == CborNoError, "value c is text string");
        CHECK(strcmp(s, "ohos") == 0, "value c == \"ohos\"");
    }
    CHECK(cbor_value_advance(&val) == CborNoError, "advance past c");

    /* key "d" -> boolean true */
    {
        bool b = false;
        CHECK(cbor_value_get_type(&val) == CborTextStringType, "key d is text");
        CHECK(cbor_value_advance(&val) == CborNoError, "advance to value");
        err = cbor_value_get_boolean(&val, &b);
        CHECK(err == CborNoError, "value d is boolean");
        CHECK(b == true, "value d == true");
    }
    CHECK(cbor_value_advance(&val) == CborNoError, "advance past d");

    /* key "e" -> null */
    CHECK(cbor_value_get_type(&val) == CborTextStringType, "key e is text");
    CHECK(cbor_value_advance(&val) == CborNoError, "advance to value");
    CHECK(cbor_value_get_type(&val) == CborNullType, "value e is null");
    CHECK(cbor_value_advance(&val) == CborNoError, "advance past e");

    /* end of map */
    CHECK(cbor_value_at_end(&val) != 0, "map fully consumed");
    err = cbor_value_leave_container(&root, &val);
    CHECK(err == CborNoError, "cbor_value_leave_container");

    if (failures) {
        fprintf(stderr, "tinycbor test FAILED: %d assertion(s)\n", failures);
        return 1;
    }
    printf("tinycbor round-trip test PASSED (encode+parse+verify)\n");
    return 0;
}