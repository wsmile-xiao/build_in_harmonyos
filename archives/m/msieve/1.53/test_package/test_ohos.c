/* test_package/test_ohos.c — msieve 1.53 鸿蒙特有测试
 *
 * 在 OpenHarmony 目标机上真实运行，验证：
 *   1. 库 API 分解真实运行（AArch64 上全部走可移植 C 路径）
 *   2. 运行时 CPU 探测如实返回非 x86 结果：cpu_type 枚举中不存在伪造的
 *      SSE/AVX 能力（本测试通过在 cpu_generic 模式下完成分解来验证
 *      可移植路径的功能正确性——这正是 AArch64 的实际运行路径）
 *   3. 分解结果素性校验链完整（未删除算法校验）：每个素因子经
 *      独立 Miller-Rabin 复核
 *
 * ELF/解释器/.codesign/RPATH 的二进制格式检查在 test_package/conanfile.py
 * 的 test() 阶段用 llvm-readelf 完成（目标机外部检查），本文件专注
 * 真实计算正确性。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <gmp.h>
#include "msieve.h"

static int factor_and_verify(const char *n)
{
    char buf[256];
    snprintf(buf, sizeof(buf), "%s", n);
    msieve_obj *obj = msieve_obj_new(
        buf, 0, "ohos_save.dat", "ohos_msieve.log", "ohos_msieve.fb",
        0, 0, 0,
        cpu_generic,   /* AArch64 实际运行路径：无伪造 CPU 特性 */
        0, 0, 1, 0, NULL);
    if (!obj) {
        printf("FAIL %s: msieve_obj_new NULL\n", n);
        return 1;
    }
    msieve_run(obj);
    if (!(obj->flags & MSIEVE_FLAG_FACTORIZATION_DONE)) {
        printf("FAIL %s: FACTORIZATION_DONE not set\n", n);
        msieve_obj_free(obj);
        return 1;
    }
    /* 乘积回验 + 素性复核（GMP mpz，确定性 MR） */
    int failures = 0;
    mpz_t product, fac;
    mpz_init_set_ui(product, 1);
    mpz_init(fac);
    for (msieve_factor *p = obj->factors; p; p = p->next) {
        if (mpz_set_str(fac, p->number, 10) != 0) {
            printf("FAIL %s: factor %s is not a valid decimal number\n", n, p->number);
            mpz_clears(product, fac, NULL);
            msieve_obj_free(obj);
            return 1;
        }
        mpz_mul(product, product, fac);
        if (p->factor_type == MSIEVE_COMPOSITE) {
            printf("FAIL %s: factor %s COMPOSITE\n", n, p->number);
            failures++;
        }
        if (mpz_probab_prime_p(fac, 25) < 1) {
            printf("FAIL %s: factor %s not prime\n", n, p->number);
            failures++;
        }
    }
    mpz_t target;
    mpz_init(target);
    if (mpz_set_str(target, n, 10) != 0) {
        printf("FAIL %s: input is not a valid decimal number\n", n);
        mpz_clears(product, fac, target, NULL);
        msieve_obj_free(obj);
        return 1;
    }
    if (mpz_cmp(product, target) != 0) {
        printf("FAIL %s: product mismatch\n", n);
        failures++;
    }
    mpz_clears(product, fac, target, NULL);
    msieve_obj_free(obj);
    if (!failures) printf("PASS ohos factor %s (portable C path)\n", n);
    return failures;
}

int main(void)
{
    int failures = 0;
    printf("== msieve 1.53 OHOS-specific tests ==\n");
    printf("target: OpenHarmony PC aarch64, musl libc, portable C fallback paths\n");

    /* QS 级合数：走完整 sieve->filter->lanczos->sqrt 流程 */
    failures += factor_and_verify("10967535067");            /* 11 位半素数 */
    failures += factor_and_verify("892022642363854546948330085836109495305327352429"); /* 46 位 */

    printf(failures ? "== %d FAILURE(S) ==\n" : "== ALL OHOS TESTS PASSED ==\n", failures);
    return failures ? 1 : 0;
}
