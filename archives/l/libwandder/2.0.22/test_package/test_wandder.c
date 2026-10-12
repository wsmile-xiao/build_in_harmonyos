/* Consumer exercise for the packaged libwandder.

   wandder_encode_finish() sizes the output from the top-level item's
   childrensize. A bare primitive has no parent, so its value length is
   not included and encode_pending() asserts. Each DER value is therefore
   encoded as the single child of a universal SEQUENCE, then decoded back.
   BER primitives are encoded with the separate BER encoder, which grows
   its own buffer. The ETSI decoder is constructed and freed.
*/
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "libwandder.h"
#include "libwandder_etsili.h"

static int checks;
static int failed;

#define CHECK(cond)                                                            \
    do {                                                                       \
        checks++;                                                              \
        if (!(cond)) {                                                         \
            failed++;                                                          \
            fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #cond);    \
        }                                                                      \
    } while (0)

typedef struct owned_buf {
    uint8_t *bytes;
    uint32_t len;
} owned_buf;

static owned_buf der_in_sequence(uint8_t encodeas, uint8_t itemclass, uint32_t idnum,
                                 void *val, uint32_t vallen) {
    wandder_encoder_t *enc;
    wandder_encoded_result_t *res;
    owned_buf out;

    out.bytes = NULL;
    out.len = 0;
    enc = init_wandder_encoder();
    CHECK(enc != NULL);
    if (enc == NULL) {
        return out;
    }
    wandder_encode_next(enc, WANDDER_TAG_SEQUENCE, WANDDER_CLASS_UNIVERSAL_CONSTRUCT, 16,
                        NULL, 0);
    wandder_encode_next(enc, encodeas, itemclass, idnum, val, vallen);
    wandder_encode_endseq(enc);
    res = wandder_encode_finish(enc);
    CHECK(res != NULL && res->encoded != NULL && res->len > 0);
    if (res != NULL && res->encoded != NULL && res->len > 0) {
        out.bytes = (uint8_t *)malloc(res->len);
        CHECK(out.bytes != NULL);
        if (out.bytes != NULL) {
            memcpy(out.bytes, res->encoded, res->len);
            out.len = res->len;
        }
        wandder_release_encoded_result(enc, res);
    }
    free_wandder_encoder(enc);
    return out;
}

static wandder_decoder_t *open_inner(const uint8_t *buf, uint32_t len) {
    wandder_decoder_t *dec;

    dec = init_wandder_decoder(NULL, (uint8_t *)buf, len, true);
    CHECK(dec != NULL);
    if (dec == NULL) {
        return NULL;
    }
    CHECK(wandder_decode_next(dec) > 0);
    CHECK(wandder_get_class(dec) == WANDDER_CLASS_UNIVERSAL_CONSTRUCT);
    CHECK(wandder_get_identifier(dec) == 16);
    CHECK(strcmp(wandder_get_tag_string(dec), "Sequence") == 0);
    CHECK(wandder_decode_next(dec) > 0);
    return dec;
}

static void test_der_octet(void) {
    static const char payload[] = "wandder";
    owned_buf res;
    wandder_decoder_t *dec;

    res = der_in_sequence(WANDDER_TAG_OCTETSTRING, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 4,
                          (void *)payload, 7);
    if (res.bytes == NULL) {
        return;
    }
    CHECK(res.len == 11);
    CHECK(res.bytes[0] == 0x30);
    CHECK(res.bytes[1] == 0x09);
    CHECK(res.bytes[2] == 0x04);
    CHECK(res.bytes[3] == 0x07);
    CHECK(memcmp(res.bytes + 4, payload, 7) == 0);
    dec = open_inner(res.bytes, res.len);
    if (dec != NULL) {
        CHECK(wandder_get_class(dec) == WANDDER_CLASS_UNIVERSAL_PRIMITIVE);
        CHECK(wandder_get_identifier(dec) == 4);
        CHECK(wandder_get_itemlen(dec) == 7);
        CHECK(memcmp(wandder_get_itemptr(dec), payload, 7) == 0);
        CHECK(strcmp(wandder_get_tag_string(dec), "Octet String") == 0);
        free_wandder_decoder(dec);
    }
    free(res.bytes);
}

static void test_der_integer(int32_t value, const uint8_t *expect, uint32_t expect_len,
                             uint32_t inner_len) {
    owned_buf res;
    wandder_decoder_t *dec;

    res = der_in_sequence(WANDDER_TAG_INTEGER, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 2, &value,
                          (uint32_t)sizeof(value));
    if (res.bytes == NULL) {
        return;
    }
    CHECK(res.len == expect_len);
    CHECK(memcmp(res.bytes, expect, expect_len) == 0);
    dec = open_inner(res.bytes, res.len);
    if (dec != NULL) {
        CHECK(wandder_get_identifier(dec) == 2);
        CHECK(wandder_get_itemlen(dec) == inner_len);
        CHECK(wandder_get_integer_value(dec->current, NULL) == (int64_t)value);
        CHECK(strcmp(wandder_get_tag_string(dec), "Integer") == 0);
        free_wandder_decoder(dec);
    }
    free(res.bytes);
}

static void test_der_null(void) {
    static const uint8_t expect[] = {0x30, 0x02, 0x05, 0x00};
    owned_buf res;
    wandder_decoder_t *dec;

    res = der_in_sequence(WANDDER_TAG_NULL, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 5, NULL, 0);
    if (res.bytes == NULL) {
        return;
    }
    CHECK(res.len == 4);
    CHECK(memcmp(res.bytes, expect, 4) == 0);
    dec = open_inner(res.bytes, res.len);
    if (dec != NULL) {
        CHECK(wandder_get_identifier(dec) == 5);
        CHECK(wandder_get_itemlen(dec) == 0);
        CHECK(strcmp(wandder_get_tag_string(dec), "NULL") == 0);
        free_wandder_decoder(dec);
    }
    free(res.bytes);
}

static void test_ber_octet(void) {
    static const char payload[] = "hi";
    wandder_encoder_ber_t *enc;
    wandder_encoded_result_ber_t *res;
    wandder_decoder_t *dec;

    enc = wandder_init_encoder_ber(64, 32);
    CHECK(enc != NULL);
    if (enc == NULL) {
        return;
    }
    wandder_encode_next_ber(enc, WANDDER_TAG_OCTETSTRING, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 4,
                            (void *)payload, 2);
    res = wandder_encode_finish_ber(enc);
    wandder_free_encoder_ber(enc);
    CHECK(res != NULL && res->buf != NULL);
    if (res == NULL || res->buf == NULL) {
        wandder_free_encoded_result_ber(res);
        return;
    }
    CHECK(res->len == 4);
    CHECK(res->buf[0] == 0x04);
    CHECK(res->buf[1] == 0x02);
    CHECK(memcmp(res->buf + 2, payload, 2) == 0);
    dec = init_wandder_decoder(NULL, res->buf, (uint32_t)res->len, true);
    CHECK(dec != NULL);
    if (dec != NULL) {
        CHECK(wandder_decode_next(dec) > 0);
        CHECK(wandder_get_itemlen(dec) == 2);
        CHECK(memcmp(wandder_get_itemptr(dec), payload, 2) == 0);
        free_wandder_decoder(dec);
    }
    wandder_free_encoded_result_ber(res);
}

static void test_ber_integer(void) {
    int32_t value = 42;
    wandder_encoder_ber_t *enc;
    wandder_encoded_result_ber_t *res;
    wandder_decoder_t *dec;

    enc = wandder_init_encoder_ber(64, 32);
    CHECK(enc != NULL);
    if (enc == NULL) {
        return;
    }
    wandder_encode_next_ber(enc, WANDDER_TAG_INTEGER, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 2, &value,
                            (uint32_t)sizeof(value));
    res = wandder_encode_finish_ber(enc);
    wandder_free_encoder_ber(enc);
    CHECK(res != NULL && res->buf != NULL && res->len > 2);
    if (res == NULL || res->buf == NULL) {
        wandder_free_encoded_result_ber(res);
        return;
    }
    CHECK(res->buf[0] == 0x02);
    dec = init_wandder_decoder(NULL, res->buf, (uint32_t)res->len, true);
    CHECK(dec != NULL);
    if (dec != NULL) {
        CHECK(wandder_decode_next(dec) > 0);
        CHECK(wandder_get_integer_value(dec->current, NULL) == 42);
        free_wandder_decoder(dec);
    }
    wandder_free_encoded_result_ber(res);
}

static void test_raw_integer(void) {
    uint8_t pos[] = {0x7f};
    uint8_t neg[] = {0xff};

    CHECK(wandder_decode_integer_value(pos, 1) == 127);
    CHECK(wandder_decode_integer_value(neg, 1) == -1);
}

static void test_etsili_decoder(void) {
    wandder_etsispec_t *dec;

    dec = wandder_create_etsili_decoder();
    CHECK(dec != NULL);
    wandder_free_etsili_decoder(dec);
}

static void test_reset_encoder(void) {
    wandder_encoder_t *enc;
    wandder_encoded_result_t *res;
    wandder_decoder_t *dec;
    int32_t value;

    enc = init_wandder_encoder();
    CHECK(enc != NULL);
    if (enc == NULL) {
        return;
    }
    value = 1;
    wandder_encode_next(enc, WANDDER_TAG_SEQUENCE, WANDDER_CLASS_UNIVERSAL_CONSTRUCT, 16, NULL, 0);
    wandder_encode_next(enc, WANDDER_TAG_INTEGER, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 2, &value,
                        (uint32_t)sizeof(value));
    wandder_encode_endseq(enc);
    reset_wandder_encoder(enc);
    value = 7;
    wandder_encode_next(enc, WANDDER_TAG_SEQUENCE, WANDDER_CLASS_UNIVERSAL_CONSTRUCT, 16, NULL, 0);
    wandder_encode_next(enc, WANDDER_TAG_INTEGER, WANDDER_CLASS_UNIVERSAL_PRIMITIVE, 2, &value,
                        (uint32_t)sizeof(value));
    wandder_encode_endseq(enc);
    res = wandder_encode_finish(enc);
    CHECK(res != NULL && res->encoded != NULL && res->len > 0);
    if (res != NULL && res->encoded != NULL) {
        dec = open_inner(res->encoded, res->len);
        if (dec != NULL) {
            CHECK(wandder_get_integer_value(dec->current, NULL) == 7);
            free_wandder_decoder(dec);
        }
        wandder_release_encoded_result(enc, res);
    }
    free_wandder_encoder(enc);
}

int main(void) {
    static const uint8_t int42[] = {0x30, 0x03, 0x02, 0x01, 0x2a};
    static const uint8_t int_neg[] = {0x30, 0x06, 0x02, 0x04, 0xff, 0xff, 0xff, 0xd4};
    static const uint8_t int128[] = {0x30, 0x04, 0x02, 0x02, 0x00, 0x80};

    printf("=== libwandder 2.0.22 test_package ===\n");
    test_der_octet();
    test_der_integer(42, int42, (uint32_t)sizeof(int42), 1);
    test_der_integer(-44, int_neg, (uint32_t)sizeof(int_neg), 4);
    test_der_integer(128, int128, (uint32_t)sizeof(int128), 2);
    test_der_null();
    test_ber_octet();
    test_ber_integer();
    test_raw_integer();
    test_etsili_decoder();
    test_reset_encoder();

    printf("CHECKS %d/%d passed, %d failed\n", checks - failed, checks, failed);
    printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"no_tests\",\"framework\":\"none\","
           "\"command\":\"\",\"discovered\":0,\"executed\":0,\"passed\":0,\"failed\":0,"
           "\"skipped\":0,\"reason\":\"tag 2.0.22-1 has no tests directory and no "
           "automake TESTS or check_PROGRAMS\"}\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_wandder\",\"discovered\":%d,\"passedCount\":%d}\n",
           failed == 0 ? "true" : "false", checks, checks - failed);
    if (failed == 0) {
        printf("All libwandder consumer checks PASSED.\n");
        return 0;
    }
    printf("%d libwandder consumer check(s) FAILED.\n", failed);
    return 1;
}
