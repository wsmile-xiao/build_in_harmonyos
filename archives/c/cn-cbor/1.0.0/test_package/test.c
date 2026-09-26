/*
 * test_package consumer test — cn-cbor 1.0.0
 *
 * 消费者视角验证：仅通过已安装的公开头文件 <cn-cbor/cn-cbor.h> 与公开 API
 * 使用该三方库。覆盖：编码（cn_cbor_map_create/cn_cbor_string_create/
 * cn_cbor_int_create/cn_cbor_mapput_string/cn_cbor_encoder_write）、
 * 解码（cn_cbor_decode/cn_cbor_mapget_string）与释放（cn_cbor_free），
 * 校验编码/解码往返结果与可观察输出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <cn-cbor/cn-cbor.h>

#define CHECK(cond, msg)                                \
    do {                                                \
        if (!(cond)) {                                  \
            fprintf(stderr, "FAIL: %s\n", msg);         \
            return 1;                                   \
        }                                               \
        printf("ok: %s\n", msg);                        \
    } while (0)

int main(void) {
    cn_cbor_errback err;
    cn_cbor *map = NULL, *val = NULL, *name = NULL;

    /* --- 编码：{"answer": 42, "name": "cn-cbor"} --- */
    map = cn_cbor_map_create(&err);
    CHECK(map != NULL, "cn_cbor_map_create");
    val = cn_cbor_int_create(42, &err);
    CHECK(val != NULL, "cn_cbor_int_create");
    CHECK(cn_cbor_mapput_string(map, "answer", val, &err),
          "cn_cbor_mapput_string");
    name = cn_cbor_string_create("cn-cbor", &err);
    CHECK(name != NULL, "cn_cbor_string_create");
    CHECK(cn_cbor_mapput_string(map, "name", name, &err),
          "cn_cbor_mapput_string(name)");

    uint8_t buf[128];
    ssize_t n = cn_cbor_encoder_write(buf, 0, sizeof(buf), map);
    CHECK(n > 0, "cn_cbor_encoder_write");
    CHECK(buf[0] == 0xa2, "map(2 pairs) header");

    /* --- 解码往返 --- */
    cn_cbor *dec = cn_cbor_decode(buf, (size_t)n, &err);
    CHECK(dec != NULL, "cn_cbor_decode");
    cn_cbor *got = cn_cbor_mapget_string(dec, "answer");
    CHECK(got != NULL, "cn_cbor_mapget_string(answer)");
    /* 上游 cn_cbor_int_create：value>=0 存储为 CN_CBOR_UINT/v.uint，
       负数为 CN_CBOR_INT/v.sint（cn-create.c:70-76） */
    CHECK(got->type == CN_CBOR_UINT && got->v.uint == 42,
          "decoded answer == 42");
    got = cn_cbor_mapget_string(dec, "name");
    CHECK(got != NULL, "cn_cbor_mapget_string(name)");
    CHECK(got->type == CN_CBOR_TEXT && got->length == strlen("cn-cbor") &&
          memcmp(got->v.str, "cn-cbor", strlen("cn-cbor")) == 0,
          "decoded name == cn-cbor");

    printf("PASS: cn-cbor round-trip (encode/decode) OK\n");
    cn_cbor_free(dec);
    cn_cbor_free(map);
    return 0;
}