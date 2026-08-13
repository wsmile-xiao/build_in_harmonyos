/* 真实断言：起 Singular 内核，在 Q[x,y] 上做一次可手算的多项式乘法。 */
#include <cstdio>
#include <cstring>
#include <singular/Singular/libsingular.h>

int main() {
    siInit((char *)"/nonexistent-singular-lib");   /* 内核起来即可，不需要 .lib 库 */
    /* 建环 Q[x,y] */
    char *n[2]; n[0] = omStrDup("x"); n[1] = omStrDup("y");
    ring R = rDefault(0, 2, n);
    if (!R) { std::fprintf(stderr, "rDefault 失败\n"); return 1; }
    rChangeCurrRing(R);
    /* p = x, q = y, p*q 的项数必须是 1（单项式 xy） */
    poly p = p_ISet(1, R); p_SetExp(p, 1, 1, R); p_Setm(p, R);
    poly q = p_ISet(1, R); p_SetExp(q, 2, 1, R); p_Setm(q, R);
    poly prod = pp_Mult_qq(p, q, R);
    int len = pLength(prod);
    if (len != 1) { std::fprintf(stderr, "x*y 应为 1 项，实得 %d\n", len); return 1; }
    /* 指数：x 的次数与 y 的次数都必须是 1 */
    if (p_GetExp(prod, 1, R) != 1 || p_GetExp(prod, 2, R) != 1) {
        std::fprintf(stderr, "x*y 的指数不对\n"); return 1;
    }
    std::printf("singular: Q[x,y] 上 x*y 得单项式、次数(1,1) 通过\n");
    return 0;
}
