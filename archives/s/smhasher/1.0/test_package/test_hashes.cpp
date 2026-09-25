// test_hashes — call every hash in the upstream g_hashes table (except the
// three do-nothing call-overhead stubs) and verify determinism plus
// input sensitivity. Mirrors the spirit of upstream SelfTest().
#include <cstdio>
#include <cstring>

#include "Hashes.h"

struct HashCase {
    const char *name;
    void (*fn)(const void *key, int len, uint32_t seed, void *out);
    int outbytes;
};

static const HashCase kHashes[] = {
    {"crc32", crc32, 4},
    {"md5_32", md5_32, 4},
    {"sha1_32a", sha1_32a, 4},
    {"FNV", FNV, 4},
    {"Bernstein", Bernstein, 4},
    {"lookup3", lookup3_test, 4},
    {"SuperFastHash", SuperFastHash, 4},
    {"MurmurOAAT", MurmurOAAT_test, 4},
    {"Crap8", Crap8_test, 4},
    {"City64", CityHash64_test, 8},
    {"City128", CityHash128_test, 16},
    {"Spooky32", SpookyHash32_test, 4},
    {"Spooky64", SpookyHash64_test, 8},
    {"Spooky128", SpookyHash128_test, 16},
    {"MurmurHash1", MurmurHash1_test, 4},
    {"Murmur2", MurmurHash2_test, 4},
    {"Murmur2A", MurmurHash2A_test, 4},
    {"Murmur2B", MurmurHash64A_test, 8},
    {"Murmur2C", MurmurHash64B_test, 8},
};

int main(void) {
    const char *k1 = "hello world";
    const char *k2 = "hello world!";
    int checks = 0;
    int failed = 0;

    for (unsigned i = 0; i < sizeof(kHashes) / sizeof(kHashes[0]); i++) {
        const HashCase &hc = kHashes[i];
        unsigned char o1[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        unsigned char o2[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
        unsigned char o3[16] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};

        hc.fn(k1, 11, 0, o1);
        hc.fn(k1, 11, 0, o2);
        checks++;
        if (memcmp(o1, o2, hc.outbytes) != 0) {
            printf("FAIL: %s not deterministic\n", hc.name);
            failed++;
        }

        hc.fn(k2, 12, 0, o3);
        checks++;
        if (memcmp(o1, o3, hc.outbytes) == 0) {
            printf("FAIL: %s insensitive to input\n", hc.name);
            failed++;
        }

        printf("%-14s ok (", hc.name);
        for (int b = 0; b < hc.outbytes; b++) {
            printf("%02x", o1[b]);
        }
        printf(")\n");
    }

    printf("test_hashes: %d checks, %d failed\n", checks, failed);
    return failed == 0 ? 0 : 1;
}
