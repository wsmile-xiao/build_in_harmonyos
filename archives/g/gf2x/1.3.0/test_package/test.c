/* 真实断言：GF(2)[x] 上的多项式乘法。多项式按位表示（bit i = x^i 的系数），
 * 结果可以纯手算——GF(2) 上系数模 2，所以交叉项会两两抵消。 */
#include <stdio.h>
#include <gf2x.h>

static int mul_eq(unsigned long a0, unsigned long b0, unsigned long want, const char *what) {
    unsigned long a[1] = {a0}, b[1] = {b0}, c[2] = {0, 0};
    int rc = gf2x_mul(c, a, 1UL, b, 1UL);
    if (rc != 0) { fprintf(stderr, "gf2x_mul 返回 %d\n", rc); return 1; }
    if (c[0] != want) {
        fprintf(stderr, "%s: 期望 0x%lx，实得 0x%lx\n", what, want, c[0]); return 1;
    }
    return 0;
}

int main(void) {
    /* (x+1)·(x+1) = x²+2x+1 = x²+1  （GF(2) 上 2x=0）
       0b11 · 0b11 = 0b101 */
    if (mul_eq(0x3UL, 0x3UL, 0x5UL, "(x+1)^2 应为 x^2+1")) return 1;

    /* (x²+x+1)·(x+1) = x³+x²+x + x²+x+1 = x³+1
       0b111 · 0b11 = 0b1001 */
    if (mul_eq(0x7UL, 0x3UL, 0x9UL, "(x^2+x+1)(x+1) 应为 x^3+1")) return 1;

    /* x^3 · x^4 = x^7 ：0b1000 · 0b10000 = 0b10000000 */
    if (mul_eq(0x8UL, 0x10UL, 0x80UL, "x^3·x^4 应为 x^7")) return 1;

    /* 乘 1 是恒等：任意 p · 1 = p */
    if (mul_eq(0xB5UL, 0x1UL, 0xB5UL, "p·1 应为 p")) return 1;

    printf("gf2x: (x+1)^2=x^2+1、(x^2+x+1)(x+1)=x^3+1、x^3·x^4=x^7、p·1=p 全部通过\n");
    return 0;
}
