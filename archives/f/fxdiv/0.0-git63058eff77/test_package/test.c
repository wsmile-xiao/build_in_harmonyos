#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include "fxdiv.h"

/* 消费者测试 — 通过公开头文件 fxdiv.h 使用公开 API:
 * fxdiv_init_size_t / fxdiv_divide_size_t / fxdiv_quotient_size_t /
 * fxdiv_round_down_size_t / fxdiv_remainder_size_t，验证编译、链接、运行正确。 */
int main(void) {
    const size_t n = 1024u;
    const size_t d = 7u;
    int failed = 0;

    /* 预计算 magic divisor 并做一次除法（公开 API） */
    struct fxdiv_divisor_size_t divisor = fxdiv_init_size_t(d);
    struct fxdiv_result_size_t res = fxdiv_divide_size_t(n, divisor);
    if (res.quotient != n / d || res.remainder != n % d) {
        printf("fxdiv_divide_size_t FAILED: %zu / %zu = %zu r %zu (expected %zu r %zu)\n",
               n, d, res.quotient, res.remainder, n / d, n % d);
        failed = 1;
    }

    /* quotient API */
    if (fxdiv_quotient_size_t(n, divisor) != n / d) {
        printf("fxdiv_quotient_size_t FAILED\n");
        failed = 1;
    }

    /* round_down API */
    if (fxdiv_round_down_size_t(n, divisor) != (n / d) * d) {
        printf("fxdiv_round_down_size_t FAILED\n");
        failed = 1;
    }

    /* remainder API */
    if (fxdiv_remainder_size_t(n, divisor) != n % d) {
        printf("fxdiv_remainder_size_t FAILED\n");
        failed = 1;
    }

    /* uint32_t 族 */
    struct fxdiv_divisor_uint32_t d32 = fxdiv_init_uint32_t(13u);
    if (fxdiv_quotient_uint32_t(100000u, d32) != 100000u / 13u) {
        printf("fxdiv_quotient_uint32_t FAILED\n");
        failed = 1;
    }

    /* uint64_t 族（使用大除数验证 64 位路径） */
    struct fxdiv_divisor_uint64_t d64 = fxdiv_init_uint64_t(3400000000ull);
    if (fxdiv_quotient_uint64_t(100000000000000ull, d64) !=
        100000000000000ull / 3400000000ull) {
        printf("fxdiv_quotient_uint64_t FAILED\n");
        failed = 1;
    }

    if (failed) {
        printf("consumer test: FAILED\n");
        return 1;
    }
    printf("consumer test: OK (fxdiv div-by-magic-divisor on %zu-bit size_t)\n",
           sizeof(size_t) * 8);
    return 0;
}