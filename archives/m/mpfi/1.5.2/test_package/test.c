/* 真实断言：MPFI 是 MPFR 之上的**区间**运算库。
 * 断言区间的左右端点，而不是只看能不能加载——区间上下界算错是这类库最典型的缺陷。 */
#include <stdio.h>
#include <mpfi.h>

int main(void) {
    mpfi_t x, y, z;
    mpfr_t lo, hi;
    mpfi_init2(x, 200); mpfi_init2(y, 200); mpfi_init2(z, 200);
    mpfr_init2(lo, 200); mpfr_init2(hi, 200);

    /* 精确值：2 × 3 = 6，区间应退化成 [6,6] */
    mpfi_set_si(x, 2); mpfi_set_si(y, 3);
    mpfi_mul(z, x, y);
    mpfi_get_left(lo, z); mpfi_get_right(hi, z);
    if (mpfr_cmp_si(lo, 6) != 0 || mpfr_cmp_si(hi, 6) != 0) {
        fprintf(stderr, "2*3 应为 [6,6]\n"); return 1;
    }

    /* 区间乘法：[1,2] × [1,2] = [1,4] */
    mpfi_interv_si(x, 1, 2); mpfi_interv_si(y, 1, 2);
    mpfi_mul(z, x, y);
    mpfi_get_left(lo, z); mpfi_get_right(hi, z);
    if (mpfr_cmp_si(lo, 1) != 0 || mpfr_cmp_si(hi, 4) != 0) {
        fprintf(stderr, "[1,2]*[1,2] 应为 [1,4]\n"); return 1;
    }

    /* 区间加法：[1,2] + [3,4] = [4,6] */
    mpfi_interv_si(x, 1, 2); mpfi_interv_si(y, 3, 4);
    mpfi_add(z, x, y);
    mpfi_get_left(lo, z); mpfi_get_right(hi, z);
    if (mpfr_cmp_si(lo, 4) != 0 || mpfr_cmp_si(hi, 6) != 0) {
        fprintf(stderr, "[1,2]+[3,4] 应为 [4,6]\n"); return 1;
    }

    printf("mpfi: 2*3=[6,6]、[1,2]*[1,2]=[1,4]、[1,2]+[3,4]=[4,6] 全部通过\n");
    mpfr_clear(lo); mpfr_clear(hi);
    mpfi_clear(x); mpfi_clear(y); mpfi_clear(z);
    return 0;
}
