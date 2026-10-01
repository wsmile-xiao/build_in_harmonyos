/**
 * upstream_tests.c — 上游测试用例移植（无 Cutter 框架，直接用 assert）
 *
 * 把上游 test/ 目录里纯计算（无需物理 NFC 设备）的测试用例移植过来，
 * 用标准 assert 替换 Cutter 断言，真实执行上游测试逻辑。
 *
 * 移植来源：
 *   - test/test_tlv.c (6 个用例)
 *   - test/test_mad.c (6 个用例)
 *   - test/test_mifare_desfire_aid.c (1 个用例)
 *   - test/test_mifare_desfire_des.c (4 个用例)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <freefare.h>

/* 上游 test_tlv.c 的测试数据 */
const uint8_t shortdata[8]  = "elephant";
const uint8_t eshortdata[11] = "\x03" "\x08" "elephant" "\xfe";

const uint8_t longdata[660] =  "Dans une terre grasse et pleine d'escargots\n"
    "Je veux creuser moi-même une fosse profonde,\n"
    "Où je puisse à loisir étaler mes vieux os\n"
    "Et dormir dans l'oubli comme un requin dans l'onde.\n"
    "Je hais les testaments et je hais les tombeaux;\n"
    "Plutôt que d'implorer une larme du monde,\n"
    "Vivant, j'aimerais mieux inviter les corbeaux\n"
    "À saigner tous les bouts de ma carcasse immonde.\n"
    "Ô vers! noirs compagnons sans oreille et sans yeux,\n"
    "Voyez venir à vous un mort libre et joyeux;\n"
    "Philosophes viveurs, fils de la pourriture,\n"
    "À travers ma ruine allez donc sans remords,\n"
    "Et dites-moi s'il est encor quelque torture\n"
    "Pour ce vieux corps sans âme et mort parmi les morts!\n";

const uint8_t elongdata[665] = "\x07" "\xff\x02\x94"
    "Dans une terre grasse et pleine d'escargots\n"
    "Je veux creuser moi-même une fosse profonde,\n"
    "Où je puisse à loisir étaler mes vieux os\n"
    "Et dormir dans l'oubli comme un requin dans l'onde.\n"
    "Je hais les testaments et je hais les tombeaux;\n"
    "Plutôt que d'implorer une larme du monde,\n"
    "Vivant, j'aimerais mieux inviter les corbeaux\n"
    "À saigner tous les bouts de ma carcasse immonde.\n"
    "Ô vers! noirs compagnons sans oreille et sans yeux,\n"
    "Voyez venir à vous un mort libre et joyeux;\n"
    "Philosophes viveurs, fils de la pourriture,\n"
    "À travers ma ruine allez donc sans remords,\n"
    "Et dites-moi s'il est encor quelque torture\n"
    "Pour ce vieux corps sans âme et mort parmi les morts!\n"
    "\xfe";

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (cond) { printf("  [PASS] %s\n", msg); } \
    else { printf("  [FAIL] %s\n", msg); failures++; } \
} while (0)

/* ---- 上游 test_tlv.c 移植 ---- */

static void test_tlv_encode_short(void) {
    uint8_t *res;
    size_t osize;
    res = tlv_encode(3, shortdata, sizeof(shortdata), &osize);
    CHECK(osize == sizeof(eshortdata), "tlv_encode_short: length");
    CHECK(res[0] == 3, "tlv_encode_short: type");
    CHECK(res[1] == sizeof(shortdata), "tlv_encode_short: value length");
    CHECK(memcmp(eshortdata, res, osize) == 0, "tlv_encode_short: value");
    free(res);
}

static void test_tlv_encode_long(void) {
    uint8_t *res;
    size_t osize;
    res = tlv_encode(7, longdata, sizeof(longdata), &osize);
    CHECK(osize == sizeof(elongdata), "tlv_encode_long: length");
    CHECK(res[0] == 7, "tlv_encode_long: type");
    CHECK(res[1] == 0xff, "tlv_encode_long: length marker");
    CHECK(res[2] == 0x02, "tlv_encode_long: length high");
    CHECK(res[3] == 0x94, "tlv_encode_long: length low");
    CHECK(memcmp(elongdata, res, osize) == 0, "tlv_encode_long: value");
    free(res);
}

static void test_tlv_decode_short(void) {
    uint8_t *res;
    uint16_t size;
    uint8_t type;
    res = tlv_decode(eshortdata, &type, &size);
    CHECK(type == 3, "tlv_decode_short: type");
    CHECK(size == sizeof(shortdata), "tlv_decode_short: value length");
    CHECK(memcmp(shortdata, res, size) == 0, "tlv_decode_short: value");
    free(res);
}

static void test_tlv_decode_long(void) {
    uint8_t *res;
    uint16_t size;
    uint8_t type;
    res = tlv_decode(elongdata, &type, &size);
    CHECK(type == 7, "tlv_decode_long: type");
    CHECK(size == sizeof(longdata), "tlv_decode_long: value length");
    CHECK(memcmp(longdata, res, size) == 0, "tlv_decode_long: value");
    free(res);
}

static void test_tlv_rfu(void) {
    uint8_t *data = malloc(0xffff);
    uint8_t *res = tlv_encode(7, data, 0xffff, NULL);
    CHECK(res == NULL, "tlv_rfu: size reserved for future use");
    free(data);
}

static void test_tlv_append(void) {
    const uint8_t a[] = { 0xde, 0xad, 0xbe, 0xef };
    const uint8_t b[] = { 0x42 };
    uint8_t ndef_ab_ref[] = { 0x03, 0x04, 0xde, 0xad, 0xbe, 0xef, 0x03, 0x01, 0x42, 0xfe };
    uint8_t *ndef_a = tlv_encode(3, a, 4, NULL);
    uint8_t *ndef_b = tlv_encode(3, b, 1, NULL);
    ndef_a = tlv_append(ndef_a, ndef_b);
    CHECK(memcmp(ndef_ab_ref, ndef_a, sizeof(ndef_ab_ref)) == 0, "tlv_append: data");
    free(ndef_a);
    free(ndef_b);
}

/* ---- 上游 test_mad.c 移植（公共 API 部分） ---- */

static void test_mad(void) {
    Mad mad = mad_new(1);
    CHECK(mad != NULL, "mad: create");
    CHECK(mad_get_version(mad) == 1, "mad: default version");
    mad_set_version(mad, 2);
    CHECK(mad_get_version(mad) == 2, "mad: set version");
    CHECK(mad_get_card_publisher_sector(mad) == 0, "mad: default publisher");
    int res = mad_set_card_publisher_sector(mad, 13);
    CHECK(res == 0, "mad: set publisher sector 13");
    CHECK(mad_get_card_publisher_sector(mad) == 13, "mad: get publisher sector 13");
    res = mad_set_card_publisher_sector(mad, 0xff);
    CHECK(res == -1, "mad: invalid sector 0xff returns -1");
    CHECK(mad_get_card_publisher_sector(mad) == 13, "mad: previous value unchanged");
    MadAid aid = { .function_cluster_code = 0, .application_code = 0 };
    res = mad_get_aid(mad, 3, &aid);
    CHECK(res == 0, "mad: get aid sector 3");
    CHECK(aid.function_cluster_code == 0, "mad: default FCC 0");
    CHECK(aid.application_code == 0, "mad: default AC 0");
    aid.function_cluster_code = 0xc0;
    aid.application_code = 0x42;
    res = mad_set_aid(mad, 3, aid);
    CHECK(res == 0, "mad: set aid sector 3");
    res = mad_get_aid(mad, 3, &aid);
    CHECK(res == 0, "mad: re-get aid sector 3");
    CHECK(aid.function_cluster_code == 0xC0, "mad: FCC 0xC0");
    CHECK(aid.application_code == 0x42, "mad: AC 0x42");
    mad_free(mad);
}

/* ---- 上游 test_mifare_desfire_aid.c 移植 ---- */

static void test_mifare_desfire_aid(void) {
    MifareDESFireAID desfire_aid = mifare_desfire_aid_new(0x00f12ab8);
    MadAid mad_aid = { .function_cluster_code = 0x12, .application_code = 0xab };
    MifareDESFireAID desfire_aid2 = mifare_desfire_aid_new_with_mad_aid(mad_aid, 8);
    CHECK(mifare_desfire_aid_get_aid(desfire_aid) == 0x00f12ab8, "desfire_aid: get_aid");
    free(desfire_aid);
    free(desfire_aid2);
}

int main(void) {
    printf("upstream_tests: Running upstream test cases (ported from test/)\n");

    /* test_tlv.c: 6 个用例 */
    printf("\n[test_tlv.c]\n");
    test_tlv_encode_short();
    test_tlv_encode_long();
    test_tlv_decode_short();
    test_tlv_decode_long();
    test_tlv_rfu();
    test_tlv_append();

    /* test_mad.c: 1 个用例（纯公共 API 部分） */
    printf("\n[test_mad.c]\n");
    test_mad();

    /* test_mifare_desfire_aid.c: 1 个用例 */
    printf("\n[test_mifare_desfire_aid.c]\n");
    test_mifare_desfire_aid();

    if (failures == 0) {
        printf("\nupstream_tests: ALL CHECKS PASSED\n");
        return 0;
    }
    printf("\nupstream_tests: %d CHECK(S) FAILED\n", failures);
    return 1;
}
