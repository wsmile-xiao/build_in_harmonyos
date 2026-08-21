/*
 * test.c — Simple zix API test.
 *
 * Verifies that:
 *   1. zix_digest32() computes a hash of a buffer
 *   2. zix_digest64() computes a 64-bit hash
 *   3. Hash results are deterministic (same input → same output)
 *   4. Different inputs produce different hashes
 */
#include <zix/digest.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;

    const char *data = "Hello zix on HarmonyOS!";
    size_t len = strlen(data);

    /* Test 1: zix_digest32 produces a non-zero hash */
    uint32_t hash32 = zix_digest32(0, data, len);
    if (hash32 == 0) {
        fprintf(stderr, "FAIL: zix_digest32() returned 0\n");
        failures++;
    } else {
        printf("PASS: zix_digest32() = 0x%08x\n", hash32);
    }

    /* Test 2: zix_digest64 produces a non-zero hash */
    uint64_t hash64 = zix_digest64(0, data, len);
    if (hash64 == 0) {
        fprintf(stderr, "FAIL: zix_digest64() returned 0\n");
        failures++;
    } else {
        printf("PASS: zix_digest64() = 0x%016llx\n", (unsigned long long)hash64);
    }

    /* Test 3: Deterministic — same input → same output */
    uint32_t hash32_b = zix_digest32(0, data, len);
    if (hash32 != hash32_b) {
        fprintf(stderr, "FAIL: zix_digest32() not deterministic\n");
        failures++;
    } else {
        printf("PASS: zix_digest32() is deterministic\n");
    }

    /* Test 4: Different input → different hash */
    uint32_t hash32_c = zix_digest32(0, "Different input", 15);
    if (hash32 == hash32_c) {
        fprintf(stderr, "FAIL: zix_digest32() collision for different inputs\n");
        failures++;
    } else {
        printf("PASS: zix_digest32() produces different hashes for different inputs\n");
    }

    if (failures > 0) {
        fprintf(stderr, "\n%d test(s) FAILED\n", failures);
        return 1;
    }

    printf("\nAll zix tests passed.\n");
    return 0;
}
