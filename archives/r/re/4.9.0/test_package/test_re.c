/*
 * test_re.c — re (libre) 4.9.0 L1 test
 * Verifies: library version string, basic SHA-1 hash, memory reference
 */
#include <stdio.h>
#include <string.h>
#include <re/re.h>

int main(void) {
    int passed = 0;
    int total = 3;

    /* Test 1: Version string via sys_libre_version_get */
    const char *version = sys_libre_version_get();
    if (version && strstr(version, "4.9.0")) {
        printf("[PASS] libre version: %s\n", version);
        passed++;
    } else {
        printf("[FAIL] libre version: %s\n", version ? version : "NULL");
    }

    /* Test 2: SHA-1 hash via sha1() */
    uint8_t hash[20] = {0};
    const char *msg = "Hello, libre!";
    uint8_t expected[20] = {
        0x54, 0x73, 0x31, 0x9f, 0x91, 0xd3, 0x8e, 0x62, 0x42, 0x91,
        0xfa, 0x6d, 0xdf, 0xff, 0x83, 0x8a, 0x3e, 0x88, 0x3f, 0x1f
    };
    sha1((const uint8_t *)msg, strlen(msg), hash);
    if (memcmp(hash, expected, 20) == 0) {
        printf("[PASS] SHA-1 hash matches expected\n");
        passed++;
    } else {
        printf("[FAIL] SHA-1 hash mismatch\n");
    }

    /* Test 3: mem_ref/mem_deref with heap-allocated memory */
    uint8_t *buf = (uint8_t *)mem_alloc(32, NULL);
    if (!buf) {
        printf("[FAIL] mem_alloc returned NULL\n");
        printf("\n=== %d/%d tests passed ===\n", passed, total);
        return 1;
    }
    memset(buf, 0xAB, 32);
    void *m = mem_ref(buf);
    if (m) {
        printf("[PASS] mem_ref works\n");
        passed++;
        mem_deref(m);
    } else {
        printf("[FAIL] mem_ref returned NULL\n");
    }
    mem_deref(buf);

    printf("\n=== %d/%d tests passed ===\n", passed, total);
    return (passed == total) ? 0 : 1;
}