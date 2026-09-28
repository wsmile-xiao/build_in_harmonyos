/* Consumer test for the installed libyubikey package.
 *
 * Uses only the public API from yubikey.h with the known-answer vectors
 * from the upstream tests/selftest.c, plus the package's public size
 * constants. Exercises linking (libyubikey) and headers (yubikey.h).
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "yubikey.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg)                       \
    do {                                       \
        checks++;                              \
        if (!(cond)) {                         \
            failures++;                        \
            fprintf(stderr, "FAIL: %s\n", msg); \
        }                                      \
    } while (0)

int main(void) {
    /* Public constants. */
    CHECK(YUBIKEY_BLOCK_SIZE == 16, "YUBIKEY_BLOCK_SIZE == 16");
    CHECK(YUBIKEY_KEY_SIZE == 16, "YUBIKEY_KEY_SIZE == 16");
    CHECK(YUBIKEY_UID_SIZE == 6, "YUBIKEY_UID_SIZE == 6");
    CHECK(YUBIKEY_OTP_SIZE == 32, "YUBIKEY_OTP_SIZE == 32");
    CHECK(YUBIKEY_CRC_OK_RESIDUE == 0xf0b8, "YUBIKEY_CRC_OK_RESIDUE == 0xf0b8");

    /* ModHex codec (upstream modhex-1 / modhex-2 vectors). */
    char buf[64];
    char back[64];
    yubikey_modhex_encode(buf, "test", 4);
    CHECK(strcmp(buf, "ifhgieif") == 0, "modhex encode 'test' -> ifhgieif");
    yubikey_modhex_decode(back, buf, 8);
    CHECK(memcmp(back, "test", 4) == 0, "modhex decode roundtrip");
    CHECK(yubikey_modhex_p("cbdefghijklnrtuv") == 1, "modhex_p accepts modhex alphabet");
    CHECK(yubikey_modhex_p("xyz") == 0, "modhex_p rejects non-modhex letters");

    /* Hex codec (upstream hex-2 vectors). */
    yubikey_hex_encode(buf, "test", 4);
    CHECK(strcmp(buf, "74657374") == 0, "hex encode 'test' -> 74657374");
    yubikey_hex_decode(back, buf, 8);
    CHECK(memcmp(back, "test", 4) == 0, "hex decode roundtrip");
    CHECK(yubikey_hex_p("0123456789abcdef") == 1, "hex_p accepts hex alphabet");
    CHECK(yubikey_hex_p("0123Xabc") == 0, "hex_p rejects non-hex characters");

    /* CRC16 (upstream crc-1/2/3/4 vectors). */
    unsigned char crc_a[] = {0, 1, 2, 3, 4};
    CHECK(yubikey_crc16(crc_a, sizeof(crc_a)) == 62919, "crc16 {0,1,2,3,4} == 62919");
    unsigned char crc_b[] = {0xfe};
    CHECK(yubikey_crc16(crc_b, sizeof(crc_b)) == 4470, "crc16 {0xfe} == 4470");
    unsigned char crc_c[] = {0x55, 0xaa, 0, 0xff};
    CHECK(yubikey_crc16(crc_c, sizeof(crc_c)) == 52149, "crc16 {55,aa,00,ff} == 52149");
    unsigned char crc_d[] = {0x01, 0x02, 0x03, 0x04, 0x05, 0x06,
                             0x30, 0x75, 0x00, 0x09, 0x3d, 0xfa, 0x60, 0xea};
    CHECK(yubikey_crc16(crc_d, sizeof(crc_d)) == 35339, "crc14-byte vector == 35339");

    /* AES-128 block decrypt/encrypt (upstream aes-1 vectors). */
    uint8_t block[17];
    uint8_t key[17];
    memcpy(block, "0123456789abcdef", 17);
    memcpy(key, "abcdef0123456789", 17);
    yubikey_aes_decrypt(block, key);
    CHECK(memcmp(block,
                 "\x83\x8a\x46\x7f\x34\x63\x95\x51"
                 "\x75\x5b\xd3\x2a\x4a\x2f\x15\xe1",
                 16) == 0,
          "aes decrypt known-answer vector");
    yubikey_aes_encrypt(block, key);
    CHECK(memcmp(block, "0123456789abcdef", 16) == 0, "aes encrypt restores plaintext");

    /* OTP generate + parse roundtrip (upstream otp-1 flow).  generate()
     * encrypts the token struct in place, so compare the parsed result
     * against a saved copy of the original bytes, not against tok. */
    static const uint8_t tok_orig[16] = {
        0x16, 0xe1, 0xe5, 0xd9, 0xd3, 0x99, 0x10, 0x04,
        0x45, 0x20, 0x07, 0xe3, 0x02, 0x00, 0x00, 0x00,
    };
    yubikey_token_st tok;
    yubikey_token_st parsed;
    memcpy(&tok, tok_orig, 16);
    char otp[YUBIKEY_OTP_SIZE + 1];
    yubikey_generate(&tok, key, otp);
    yubikey_parse((const uint8_t *) otp, key, &parsed);
    CHECK(memcmp(&parsed, tok_orig, 16) == 0, "otp generate/parse roundtrip");
    CHECK(strlen(otp) == YUBIKEY_OTP_SIZE, "otp string length == 32");

    printf("libyubikey test_package: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
