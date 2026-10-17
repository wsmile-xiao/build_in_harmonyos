#include <aes.h>

#include <cstddef>
#include <cstdio>
#include <vector>

#ifndef __OHOS__
#error "test_tiny_aes_c must be compiled for HarmonyOS"
#endif

namespace {

int failures = 0;
int assertions = 0;

void check(bool condition, const char* message) {
    ++assertions;
    if (!condition) {
        std::fprintf(stderr, "FAIL: %s\n", message);
        ++failures;
    }
}

}  // namespace

int main() {
    const aes_key_t key = {
        0x60, 0x3d, 0xeb, 0x10, 0x15, 0xca, 0x71, 0xbe,
        0x2b, 0x73, 0xae, 0xf0, 0x85, 0x7d, 0x77, 0x81,
        0x1f, 0x35, 0x2c, 0x07, 0x3b, 0x61, 0x08, 0xd7,
        0x2d, 0x98, 0x10, 0xa3, 0x09, 0x14, 0xdf, 0xf4,
    };
    const aes_block_t initial_counter = {
        0xf0, 0xf1, 0xf2, 0xf3, 0xf4, 0xf5, 0xf6, 0xf7,
        0xf8, 0xf9, 0xfa, 0xfb, 0xfc, 0xfd, 0xfe, 0xff,
    };
    const std::vector<aes_block_t> plaintext = {
        {0x6b, 0xc1, 0xbe, 0xe2, 0x2e, 0x40, 0x9f, 0x96,
         0xe9, 0x3d, 0x7e, 0x11, 0x73, 0x93, 0x17, 0x2a},
        {0xae, 0x2d, 0x8a, 0x57, 0x1e, 0x03, 0xac, 0x9c,
         0x9e, 0xb7, 0x6f, 0xac, 0x45, 0xaf, 0x8e, 0x51},
        {0x30, 0xc8, 0x1c, 0x46, 0xa3, 0x5c, 0xe4, 0x11,
         0xe5, 0xfb, 0xc1, 0x19, 0x1a, 0x0a, 0x52, 0xef},
        {0xf6, 0x9f, 0x24, 0x45, 0xdf, 0x4f, 0x9b, 0x17,
         0xad, 0x2b, 0x41, 0x7b, 0xe6, 0x6c, 0x37, 0x10},
    };
    const std::vector<aes_block_t> ciphertext = {
        {0x60, 0x1e, 0xc3, 0x13, 0x77, 0x57, 0x89, 0xa5,
         0xb7, 0xa7, 0xf5, 0x04, 0xbb, 0xf3, 0xd2, 0x28},
        {0xf4, 0x43, 0xe3, 0xca, 0x4d, 0x62, 0xb5, 0x9a,
         0xca, 0x84, 0xe9, 0x90, 0xca, 0xca, 0xf5, 0xc5},
        {0x2b, 0x09, 0x30, 0xda, 0xa2, 0x3d, 0xe9, 0x4c,
         0xe8, 0x70, 0x17, 0xba, 0x2d, 0x84, 0x98, 0x8d},
        {0xdf, 0xc9, 0xc5, 0x8d, 0xb6, 0x7a, 0xad, 0xa6,
         0x13, 0xc2, 0xdd, 0x08, 0x45, 0x79, 0x41, 0xa6},
    };

    auto blocks = plaintext;
    aesctr256(blocks, key, initial_counter);
    for (std::size_t i = 0; i < ciphertext.size(); ++i) {
        check(blocks[i] == ciphertext[i], "NIST AES-256-CTR ciphertext block");
    }

    const auto encrypted_blocks = blocks;
    aesctr256(blocks, key, initial_counter);
    check(blocks == plaintext, "vector API decrypts by repeating CTR");

    auto single = plaintext.front();
    aesctr256(single, key, initial_counter);
    check(single == ciphertext.front(), "single-block API matches NIST vector");
    check(single == encrypted_blocks.front(), "single and vector APIs agree");
    aesctr256(single, key, initial_counter);
    check(single == plaintext.front(), "single-block API decrypts by repeating CTR");

    aes_block_t simple_counter{};
    aesctr256_increment_v(simple_counter);
    aes_block_t simple_expected{};
    simple_expected.back() = 1;
    check(simple_counter == simple_expected, "counter increments the low byte");

    aes_block_t carry_counter{};
    carry_counter[14] = 0x7a;
    carry_counter[15] = 0xff;
    auto carry_expected = carry_counter;
    carry_expected[14] = 0x7b;
    carry_expected[15] = 0x00;
    aesctr256_increment_v(carry_counter);
    check(carry_counter == carry_expected, "counter carries in big-endian order");

    aes_block_t wrap_counter{};
    wrap_counter.fill(0xff);
    aesctr256_increment_v(wrap_counter);
    check(wrap_counter == aes_block_t{}, "counter wraps after the maximum value");

    std::vector<aes_block_t> empty;
    aesctr256(empty, key, initial_counter);
    check(empty.empty(), "empty vector remains empty");

    if (failures != 0) {
        std::fprintf(
            stderr,
            "tiny-aes-c consumer test failed: %d/%d assertion(s)\n",
            failures,
            assertions
        );
        return 1;
    }

    std::printf("tiny-aes-c consumer test passed: %d assertions\n", assertions);
    return assertions == 12 ? 0 : 1;
}
