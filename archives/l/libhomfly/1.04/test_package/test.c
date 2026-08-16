/* libhomfly test_package —— 真实计算 + 字符串断言
 *
 * 断言依据：passagemath 自带 doctest（sage/libs/homfly.pyx）
 *   trefoil = '1 6 0 1  1 -1  2 1  0 -1  1 1  2 -1 0 1 1 1 2 1'
 *   homfly_polynomial_string(trefoil) == ' - L^-4 - 2L^-2 + M^2L^-2'
 * 即三叶结的 HOMFLY 多项式，取值唯一、可核对。
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <homfly.h>

int main(void) {
    /* homfly_str 取 char*（非 const），故用可写数组 */
    char trefoil[] = "1 6 0 1  1 -1  2 1  0 -1  1 1  2 -1 0 1 1 1 2 1";
    const char *expect = " - L^-4 - 2L^-2 + M^2L^-2";

    char *got = homfly_str(trefoil);
    printf("libhomfly: 三叶结 HOMFLY = [%s]\n", got ? got : "(null)");
    if (got == NULL) {
        fprintf(stderr, "libhomfly: FAIL —— homfly_str 返回 NULL\n");
        return 1;
    }
    if (strcmp(got, expect) != 0) {
        fprintf(stderr, "libhomfly: FAIL —— 期望 [%s]，实得 [%s]\n", expect, got);
        return 1;
    }

    printf("libhomfly: OK —— 真实计算断言通过\n");
    return 0;
}
