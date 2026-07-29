#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mimalloc.h>

static int tests_passed = 0;
static int tests_failed = 0;

#define TEST(name, expr) do { \
    if (!(expr)) { \
        fprintf(stderr, "FAIL: %s\n", name); \
        tests_failed++; \
    } else { \
        tests_passed++; \
    } \
} while(0)

int main() {
    // Test 1: Basic allocation
    void* p = mi_malloc(1024);
    TEST("mi_malloc(1024) != NULL", p != NULL);
    if (p) {
        // Test 2: Write to allocated memory
        memset(p, 0xAA, 1024);
        unsigned char* buf = (unsigned char*)p;
        int write_ok = 1;
        for (int i = 0; i < 1024; i++) {
            if (buf[i] != 0xAA) { write_ok = 0; break; }
        }
        TEST("write to allocated memory", write_ok);
        
        // Test 3: Realloc (use temp to avoid leak on failure)
        void* reallocd = mi_realloc(p, 2048);
        TEST("mi_realloc(1024, 2048) != NULL", reallocd != NULL);
        if (reallocd) {
            memset(reallocd, 0xBB, 2048);
            TEST("write after realloc", ((unsigned char*)reallocd)[0] == 0xBB);
            mi_free(reallocd);
        } else {
            mi_free(p);
        }
    }

    // Test 4: Multiple small allocations
    void* small_ptrs[10] = {NULL};
    int small_ok = 1;
    for (int i = 0; i < 10; i++) {
        small_ptrs[i] = mi_malloc(16);
        if (!small_ptrs[i]) { small_ok = 0; break; }
        memset(small_ptrs[i], i, 16);
    }
    TEST("10 small allocations", small_ok);
    for (int i = 0; i < 10; i++) {
        if (small_ptrs[i]) mi_free(small_ptrs[i]);
    }

    // Test 5: Large allocation
    void* big = mi_malloc(1048576); // 1MB
    TEST("mi_malloc(1MB) != NULL", big != NULL);
    if (big) {
        memset(big, 0xCC, 1048576);
        TEST("write to 1MB buffer", ((unsigned char*)big)[0] == 0xCC);
        mi_free(big);
    }

    // Test 6: mi_calloc (zero-initialized)
    void* z = mi_calloc(100, 100);
    TEST("mi_calloc != NULL", z != NULL);
    if (z) {
        int zero_ok = 1;
        unsigned char* bz = (unsigned char*)z;
        for (int i = 0; i < 10000; i++) {
            if (bz[i] != 0) { zero_ok = 0; break; }
        }
        TEST("mi_calloc is zero-initialized", zero_ok);
        mi_free(z);
    }

    // Test 7: Verify basic free doesn't crash
    void* s = mi_malloc(512);
    if (s) {
        mi_free(s);
        TEST("mi_malloc/free cycle", 1);
    }

    printf("Tests: %d passed, %d failed\n", tests_passed, tests_failed);
    return tests_failed > 0 ? 1 : 0;
}
