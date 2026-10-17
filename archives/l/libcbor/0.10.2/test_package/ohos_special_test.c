/*
 * HarmonyOS PC (aarch64-linux-ohos) 专项测试 — libcbor 0.10.2
 *
 * 独立于上游测试（不复述上游用例），针对 OHOS 平台验证：
 *   1) 16/32/64 位整型、负整型精确编码字节（对齐/端序路径）
 *   2) 大字节串(>256B)与不定长字符串的编解码回环
 *   3) 定长/不定长数组与 map 嵌套回环（内存/栈路径）
 *   4) 流式解码（stateless decoder 完整/非法输入语义）
 * 任一检查失败则以非零退出码返回，由 conan create 的 test() 捕获。
 *
 * NOTE: uses CHECK() instead of assert() so the validation still runs under
 * Release (-DNDEBUG) builds — assert() is compiled out by NDEBUG, which would
 * otherwise make the test validate nothing in CI.
 */
#include <stdio.h>
#include <stdlib.h>
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

static int test_wide_int_exact_bytes(void) {
    unsigned char buf[32];

    /* uint16 65535 -> 0x19 0xFF 0xFF */
    cbor_item_t *i16 = cbor_build_uint16(65535);
    size_t n16 = cbor_serialize_uint(i16, buf, sizeof(buf));
    CHECK(n16 == 3 && buf[0] == 0x19 && buf[1] == 0xFF && buf[2] == 0xFF);
    cbor_decref(&i16);

    /* uint32 70000 -> 0x1A 0x00 0x01 0x11 0x70 */
    cbor_item_t *i32 = cbor_build_uint32(70000);
    size_t n32 = cbor_serialize_uint(i32, buf, sizeof(buf));
    CHECK(n32 == 5 && buf[0] == 0x1A);
    CHECK(memcmp(buf + 1, "\x00\x01\x11\x70", 4) == 0);
    cbor_decref(&i32);

    /* uint64 0x1234567890ABCDEF -> 0x1B + 8 字节 */
    cbor_item_t *i64 = cbor_build_uint64(0x1234567890ABCDEFULL);
    size_t n64 = cbor_serialize_uint(i64, buf, sizeof(buf));
    CHECK(n64 == 9 && buf[0] == 0x1B);
    CHECK(memcmp(buf + 1, "\x12\x34\x56\x78\x90\xAB\xCD\xEF", 8) == 0);
    cbor_decref(&i64);

    /* negint64 0 -> -1 -> 0x3B + 8×0x00 */
    cbor_item_t *ni = cbor_build_negint64(0);
    size_t nn = cbor_serialize_negint(ni, buf, sizeof(buf));
    CHECK(nn == 9 && buf[0] == 0x3B);
    for (int k = 1; k < 9; k++) CHECK(buf[k] == 0x00);

    /* negint64 -1（n=1）-> -2 -> 0x3B + ...01 */
    unsigned char buf2[16];
    cbor_item_t *ni2 = cbor_build_negint64(1);
    size_t nn2 = cbor_serialize_negint(ni2, buf2, sizeof(buf2));
    CHECK(nn2 == 9 && buf2[0] == 0x3B);
    CHECK(buf2[1] == 0x00 && buf2[8] == 0x01);
    cbor_decref(&ni2);
    cbor_decref(&ni);

    printf("  [wide_int] PASS\n");
    return 0;
}

static int test_large_bytestring_and_indef_string(void) {
    /* 300 字节大 bytestring */
    unsigned char big[300];
    for (size_t i = 0; i < sizeof(big); i++) big[i] = (unsigned char)(i * 7 + 3);
    cbor_item_t *bs = cbor_build_bytestring(big, sizeof(big));
    CHECK(bs != NULL);
    size_t cap = cbor_serialized_size(bs);
    unsigned char *buf = malloc(cap);
    CHECK(buf != NULL);
    size_t len = cbor_serialize(bs, buf, cap);
    cbor_decref(&bs);

    struct cbor_load_result res;
    cbor_item_t *d = cbor_load(buf, len, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_bytestring_length(d) == sizeof(big));
    CHECK(memcmp(cbor_bytestring_handle(d), big, sizeof(big)) == 0);
    cbor_decref(&d);
    free(buf);

    /* 不定长字符串：3 个 chunk */
    cbor_item_t *s = cbor_new_indefinite_string();
    cbor_string_add_chunk(s, cbor_move(cbor_build_string("Hello ")));
    cbor_string_add_chunk(s, cbor_move(cbor_build_string("HarmonyOS ")));
    cbor_string_add_chunk(s, cbor_move(cbor_build_string("libcbor")));
    size_t scap = cbor_serialized_size(s);
    unsigned char *sbuf = malloc(scap);
    CHECK(sbuf != NULL);
    size_t slen = cbor_serialize(s, sbuf, scap);
    cbor_decref(&s);

    cbor_item_t *sd = cbor_load(sbuf, slen, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_string_is_indefinite(sd));
    CHECK(cbor_string_chunk_count(sd) == 3);
    cbor_decref(&sd);
    free(sbuf);

    printf("  [large_bytestring+indef_string] PASS\n");
    return 0;
}

static int test_nested_map_array_roundtrip(void) {
    cbor_item_t *root = cbor_new_definite_map(2);
    cbor_map_add(root, (struct cbor_pair){
        .key = cbor_move(cbor_build_string("count")),
        .value = cbor_move(cbor_build_uint64(5))});
    cbor_item_t *arr = cbor_new_indefinite_array();
    cbor_array_push(arr, cbor_move(cbor_build_uint16(1)));
    cbor_array_push(arr, cbor_move(cbor_build_uint16(2)));
    cbor_array_push(arr, cbor_move(cbor_build_uint16(3)));
    cbor_map_add(root, (struct cbor_pair){
        .key = cbor_move(cbor_build_string("list")),
        .value = cbor_move(arr)});

    size_t cap = cbor_serialized_size(root);
    unsigned char *buf = malloc(cap);
    CHECK(buf != NULL);
    size_t len = cbor_serialize(root, buf, cap);
    cbor_decref(&root);

    struct cbor_load_result res;
    cbor_item_t *d = cbor_load(buf, len, &res);
    CHECK(res.error.code == CBOR_ERR_NONE);
    CHECK(cbor_typeof(d) == CBOR_TYPE_MAP);
    CHECK(cbor_map_size(d) == 2);
    cbor_item_t *list = cbor_map_handle(d)[1].value;
    CHECK(cbor_typeof(list) == CBOR_TYPE_ARRAY);
    CHECK(cbor_array_size(list) == 3);
    CHECK(cbor_get_int(cbor_array_get(list, 2)) == 3);
    cbor_decref(&d);
    free(buf);

    printf("  [nested_map_array] PASS\n");
    return 0;
}

static int test_streaming_decode(void) {
    /* stateless decoder 实测行为（探针验证）：
     *   完整 uint 0x01 → FINISHED (status=0) 且完整消费
     *   非法 0x1F → ERROR  (status=2)
     * 验证解码器按 CBOR 语义消费输入，不把非法输入误报成功。 */
    const struct cbor_callbacks callbacks = cbor_empty_callbacks;

    /* 完整输入 → FINISHED 且消费完整输入（uint 0x01 单字节完整消费） */
    unsigned char scalar[] = {0x01};
    struct cbor_decoder_result r = cbor_stream_decode(scalar, sizeof(scalar), &callbacks, NULL);
    CHECK(r.status == CBOR_DECODER_FINISHED);
    CHECK(r.read == sizeof(scalar));

    /* 非法输入（reserved MTB 0x1F）→ ERROR，不误报成功 */
    unsigned char bad[] = {0x1F};
    r = cbor_stream_decode(bad, sizeof(bad), &callbacks, NULL);
    CHECK(r.status == CBOR_DECODER_ERROR);

    printf("  [streaming_decode] PASS\n");
    return 0;
}

int main(void) {
    printf("HarmonyOS special test (libcbor %s) start\n", CBOR_VERSION);
    if (test_wide_int_exact_bytes() != 0) return 1;
    if (test_large_bytestring_and_indef_string() != 0) return 1;
    if (test_nested_map_array_roundtrip() != 0) return 1;
    if (test_streaming_decode() != 0) return 1;
    printf("HarmonyOS special test: ALL PASSED\n");
    return 0;
}
