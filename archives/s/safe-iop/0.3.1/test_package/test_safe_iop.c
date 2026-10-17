#include <limits.h>
#include <stdint.h>
#include <stdio.h>

#include <safe_iop.h>

#define CHECK(condition)                                                      \
    do {                                                                      \
        if (!(condition)) {                                                   \
            fprintf(stderr, "CHECK failed: %s (line %d)\n", #condition,     \
                    __LINE__);                                                \
            return 1;                                                         \
        }                                                                     \
    } while (0)

int main(void) {
    int32_t signed_result = 0;
    uint32_t unsigned_result = 0;

    CHECK(safe_add(&signed_result, (int32_t)100, (int32_t)23) == 1 &&
          signed_result == 123);
    CHECK(safe_add(&signed_result, (int32_t)INT32_MAX, (int32_t)1) == 0);
    CHECK(safe_sub(&signed_result, (int32_t)100, (int32_t)23) == 1 &&
          signed_result == 77);
    CHECK(safe_sub(&unsigned_result, (uint32_t)0, (uint32_t)1) == 0);
    CHECK(safe_mul(&signed_result, (int32_t)12, (int32_t)11) == 1 &&
          signed_result == 132);
    CHECK(safe_mul(&unsigned_result, (uint32_t)UINT32_MAX, (uint32_t)2) == 0);
    CHECK(safe_div(&signed_result, (int32_t)144, (int32_t)12) == 1 &&
          signed_result == 12);
    CHECK(safe_div(&signed_result, (int32_t)5, (int32_t)0) == 0);
    CHECK(safe_mod(&signed_result, (int32_t)23, (int32_t)5) == 1 &&
          signed_result == 3);
    CHECK(safe_add3(&signed_result, (int32_t)1, (int32_t)2, (int32_t)3) == 1 &&
          signed_result == 6);
    CHECK(safe_mul4(&signed_result, (int32_t)2, (int32_t)3, (int32_t)4,
                    (int32_t)5) == 1 && signed_result == 120);
    CHECK(safe_iopf(&unsigned_result, "u32+", (uint32_t)100,
                    (uint32_t)23) == 1 && unsigned_result == 123);

    puts("safe-iop consumer API checks: 12/12 passed");
    return 0;
}
