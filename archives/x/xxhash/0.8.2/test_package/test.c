#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* No XXH_INLINE_ALL: use compiled symbols from libxxhash.a (real link verification) */
#include <xxhash.h>

/* Known-answer vectors for "Hello, xxHash!" with seed=0,
   verified against upstream sanity_test on OHOS aarch64. */
#define EXPECTED_XXH32     0x4bbbeba2U
#define EXPECTED_XXH64     0x197cf9539342bf65ULL
#define EXPECTED_XXH3_64   0xdea3adc7524fc027ULL

int main(void) {
    const char *test_data = "Hello, xxHash!";
    size_t len = strlen(test_data);
    int failed = 0;

    XXH32_hash_t hash32 = XXH32(test_data, len, 0);
    if (hash32 != EXPECTED_XXH32) {
        fprintf(stderr, "FAIL XXH32: got 0x%08X, expected 0x%08X\n",
                hash32, EXPECTED_XXH32);
        failed++;
    } else {
        printf("PASS XXH32  = 0x%08X\n", hash32);
    }

    XXH64_hash_t hash64 = XXH64(test_data, len, 0);
    if (hash64 != EXPECTED_XXH64) {
        fprintf(stderr, "FAIL XXH64: got 0x%016llX, expected 0x%016llX\n",
                (unsigned long long)hash64,
                (unsigned long long)EXPECTED_XXH64);
        failed++;
    } else {
        printf("PASS XXH64  = 0x%016llX\n", (unsigned long long)hash64);
    }

    XXH64_hash_t hash3 = XXH3_64bits(test_data, len);
    if (hash3 != EXPECTED_XXH3_64) {
        fprintf(stderr, "FAIL XXH3_64bits: got 0x%016llX, expected 0x%016llX\n",
                (unsigned long long)hash3,
                (unsigned long long)EXPECTED_XXH3_64);
        failed++;
    } else {
        printf("PASS XXH3   = 0x%016llX\n", (unsigned long long)hash3);
    }

    if (failed) {
        fprintf(stderr, "test xxhash 0.8.2: %d check(s) FAILED\n", failed);
        return 1;
    }
    printf("test xxhash 0.8.2: all 3 known-answer checks passed\n");
    return 0;
}
