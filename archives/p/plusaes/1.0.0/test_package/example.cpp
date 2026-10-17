/*
 * Consumer test for plusaes 1.0.0 (test_package).
 *
 * Compiles against the *packaged* header only (find_package(plusaes) →
 * plusaes::plusaes), so a missing/renamed header or a broken CMake package
 * name fails here.  Everything runs on HarmonyOS aarch64:
 *
 *   - PLUSAES_VERSION / plusaes::version() fingerprint of the installed header
 *   - ECB (NIST SP 800-38A F.1.1) and CBC (F.2.1) known-answer vectors
 *   - CTR keystream block cross-checked against an independent OpenSSL
 *     AES-128-ECB computation, GCM spec test case 1 tag vector
 *   - ECB/CBC/CTR/GCM round trips incl. PKCS padding bookkeeping
 *   - error-path checks (invalid key size, invalid tag, padded size helper)
 *
 * 25 checks must all pass; the count is the "HarmonyOS specific test" row of
 * the PR statistics (it is *not* part of the upstream case count).
 */

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "plusaes/plusaes.hpp"

static int checks = 0;

static bool check(bool cond, const char *what) {
    if (!cond) {
        std::fprintf(stderr, "plusaes test_package: FAIL at check #%d: %s\n",
                     checks + 1, what);
        return false;
    }
    ++checks;
    return true;
}

#define CHECK(cond, what)                       \
    do {                                        \
        if (!check((cond), (what))) return 1;   \
    } while (0)

/* Compare n bytes against a lowercase hex string. */
static bool hex_equals(const unsigned char *bytes, const char *hex, std::size_t n) {
    for (std::size_t i = 0; i < n; ++i) {
        unsigned int value = 0;
        if (std::sscanf(hex + 2 * i, "%2x", &value) != 1) return false;
        if (bytes[i] != static_cast<unsigned char>(value)) return false;
    }
    return true;
}

int main() {
    /* 1. installed header identity */
    CHECK(plusaes::version() == 0x01000000u,
          "plusaes::version() reports 1.0.0 (PLUSAES_VERSION 0x01000000)");
    CHECK(PLUSAES_VERSION == 0x01000000u, "PLUSAES_VERSION macro matches release");

    /* NIST SP 800-38A F.1.1 / F.2.1 / F.5.1 material, GCM spec test case 1 */
    const unsigned char nist_key[16] = {
        0x2b, 0x7e, 0x15, 0x16, 0x28, 0xae, 0xd2, 0xa6,
        0xab, 0xf7, 0x15, 0x88, 0x09, 0xcf, 0x4f, 0x3c};
    const unsigned char nist_pt[16] = {
        0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
        0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a};
    const unsigned char ecb_ct_hex[] =
        "3ad77bb40d7a3660a89ecaf32466ef97";
    const unsigned char cbc_iv[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f};
    const char *cbc_ct_hex = "7649abac8119b246cee98e9b12e9197d";

    /* 2. ECB known answer (SP 800-38A F.1.1) */
    unsigned char ecb_out[16] = {};
    CHECK(plusaes::encrypt_ecb(nist_pt, 16, nist_key, 16, ecb_out, 16, false) ==
              plusaes::kErrorOk,
          "encrypt_ecb accepts a 16-byte unpadded block");
    CHECK(hex_equals(ecb_out, reinterpret_cast<const char *>(ecb_ct_hex), 16),
          "ECB ciphertext matches NIST SP 800-38A F.1.1");

    /* ECB decrypt always strips PKCS padding, so the round trip uses a padded
       message while the known-answer block above stays unpadded. */
    const std::string ecb_message = "Hello, plusaes!";  /* 15 bytes */
    std::vector<unsigned char> ecb_buf(
        plusaes::get_padded_encrypted_size(ecb_message.size()), 0);
    std::memcpy(&ecb_buf[0], ecb_message.data(), ecb_message.size());
    CHECK(plusaes::encrypt_ecb(&ecb_buf[0], ecb_message.size(), nist_key, 16,
                               &ecb_buf[0], ecb_buf.size(), true) ==
              plusaes::kErrorOk,
          "encrypt_ecb pads a 15-byte message");

    std::vector<unsigned char> ecb_back(ecb_buf.size(), 0);
    unsigned long ecb_padded = 0;
    CHECK(plusaes::decrypt_ecb(&ecb_buf[0], ecb_buf.size(), nist_key, 16,
                               &ecb_back[0], ecb_back.size(), &ecb_padded) ==
              plusaes::kErrorOk,
          "decrypt_ecb accepts the padded ciphertext");
    CHECK(ecb_padded == 1 &&
              ecb_buf.size() - ecb_padded == ecb_message.size() &&
              std::string(reinterpret_cast<char *>(&ecb_back[0]),
                          ecb_buf.size() - ecb_padded) == ecb_message,
          "ECB round trip restores the message; padded_size reports the pad length");

    /* 3. CBC known answer (SP 800-38A F.2.1) */
    unsigned char cbc_out[16] = {};
    CHECK(plusaes::encrypt_cbc(nist_pt, 16, nist_key, 16, &cbc_iv, cbc_out, 16,
                               false) == plusaes::kErrorOk,
          "encrypt_cbc accepts the NIST IV and a 16-byte block");
    CHECK(hex_equals(cbc_out, cbc_ct_hex, 16),
          "CBC ciphertext matches NIST SP 800-38A F.2.1");

    /* 4. CBC round trip with PKCS-style padding bookkeeping */
    const std::string message = "Hello, plusaes!";  /* 15 bytes */
    const std::vector<unsigned char> key128 =
        plusaes::key_from_string(&"EncryptionKey128");
    CHECK(key128.size() == 16, "key_from_string yields a 128-bit key");
    CHECK(plusaes::get_padded_encrypted_size(15) == 16 &&
              plusaes::get_padded_encrypted_size(16) == 32,
          "get_padded_encrypted_size pads to the next 16-byte boundary");

    std::vector<unsigned char> cbc_pad(
        plusaes::get_padded_encrypted_size(message.size()), 0);
    std::memcpy(&cbc_pad[0], message.data(), message.size());
    CHECK(plusaes::encrypt_cbc(&cbc_pad[0], message.size(), &key128[0],
                               key128.size(), &cbc_iv, &cbc_pad[0],
                               cbc_pad.size(), true) == plusaes::kErrorOk,
          "encrypt_cbc pads the 15-byte message");

    std::vector<unsigned char> cbc_plain(cbc_pad.size(), 0);
    unsigned long padded_size = 0;
    CHECK(plusaes::decrypt_cbc(&cbc_pad[0], cbc_pad.size(), &key128[0],
                               key128.size(), &cbc_iv, &cbc_plain[0],
                               cbc_plain.size(), &padded_size) == plusaes::kErrorOk,
          "decrypt_cbc accepts the padded ciphertext");
    CHECK(padded_size == 1 &&
              cbc_pad.size() - padded_size == message.size() &&
              std::string(reinterpret_cast<char *>(&cbc_plain[0]),
                          cbc_pad.size() - padded_size) == message,
          "CBC round trip restores the message; padded_size reports the pad length");

    /* 5. key helpers for the 192/256-bit sizes (the literal must be exactly
          24 / 32 characters — plusaes overloads on the array extent). */
    CHECK(plusaes::key_from_string(&"123456789012345678901234").size() == 24,
          "key_from_string yields a 192-bit key");
    CHECK(plusaes::key_from_string(&"abcdefghijklMNOPQRSTUVwxYz789012").size() == 32,
          "key_from_string yields a 256-bit key");

    /* 6. CTR round trip (SP 800-38A F.5.1 counter block) */
    const unsigned char ctr_nonce[16] = {
        0x0f, 0x0e, 0x0d, 0x0c, 0x0b, 0x0a, 0x09, 0x08,
        0x07, 0x06, 0x05, 0x04, 0x03, 0x02, 0x01, 0x00};
    unsigned char ctr_data[32] = {};
    std::memcpy(ctr_data, nist_pt, 16);
    std::memcpy(ctr_data + 16, nist_pt, 16);
    CHECK(plusaes::crypt_ctr(ctr_data, sizeof(ctr_data), nist_key, 16,
                             &ctr_nonce) == plusaes::kErrorOk,
          "crypt_ctr encrypts two blocks in place");
    CHECK(hex_equals(ctr_data,
                     "19bac1f09c67bd95679fba754cb375c7", 16),
          "CTR first block equals AES-ECB(counter) XOR plaintext (OpenSSL cross-check)");
    CHECK(plusaes::crypt_ctr(ctr_data, sizeof(ctr_data), nist_key, 16,
                             &ctr_nonce) == plusaes::kErrorOk,
          "crypt_ctr decrypts the same buffer in place");

    /* 7. GCM known answer (GCM spec test case 1: empty plaintext, K = IV = 0)
          plus a round trip and the authentication failure path. */
    unsigned char zero_key[16] = {};
    unsigned char zero_iv[12] = {};
    unsigned char gcm_tag[16] = {};
    CHECK(plusaes::encrypt_gcm(nullptr, 0, nullptr, 0, zero_key, 16, &zero_iv,
                               &gcm_tag) == plusaes::kErrorOk,
          "encrypt_gcm accepts an empty plaintext with a 12-byte IV");
    CHECK(hex_equals(gcm_tag, "58e2fccefa7e3061367f1d57a4e7455a", 16),
          "GCM tag matches the published empty-message reference vector");

    unsigned char gcm_data[31] = {};
    std::memcpy(gcm_data, "plusaes consumer round trip on OHOS", 31);
    unsigned char gcm_iv[12] = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
    unsigned char gcm_tag2[16] = {};
    CHECK(plusaes::encrypt_gcm(gcm_data, sizeof(gcm_data), nullptr, 0, nist_key,
                               16, &gcm_iv, &gcm_tag2) == plusaes::kErrorOk,
          "encrypt_gcm encrypts 31 bytes in place");
    CHECK(plusaes::decrypt_gcm(gcm_data, sizeof(gcm_data), nullptr, 0, nist_key,
                               16, &gcm_iv, &gcm_tag2) == plusaes::kErrorOk,
          "decrypt_gcm verifies the tag and restores the plaintext");
    gcm_tag2[0] ^= 0x01;
    CHECK(plusaes::decrypt_gcm(gcm_data, sizeof(gcm_data), nullptr, 0, nist_key,
                               16, &gcm_iv, &gcm_tag2) == plusaes::kErrorInvalidTag,
          "decrypt_gcm rejects a tampered authentication tag");

    /* 8. error path: invalid key size is reported, not silently accepted */
    unsigned char bad_out[16] = {};
    CHECK(plusaes::encrypt_ecb(nist_pt, 16, nist_key, 15, bad_out, 16, false) ==
              plusaes::kErrorInvalidKeySize,
          "encrypt_ecb rejects a 15-byte key");

    std::printf("plusaes test_package: %d checks passed\n", checks);
    return 0;
}
