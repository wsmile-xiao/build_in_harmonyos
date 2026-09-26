/*
 * test_package 消费者测试 — libbig_int 2.6 (OHOS aarch64)
 *
 * 仅使用已安装的公开头文件 (big_int_full.h) 与公开 API，验证第三方消费者
 * 能够编译、链接、调用并得到可观察结果：
 *   - big_int_create / big_int_destroy          内存类  (service_funcs.h)
 *   - big_int_from_int / big_int_to_int         转换类  (service_funcs.h)
 *   - big_int_add / big_int_mul / big_int_div   算术类  (basic_funcs.h)
 *   - big_int_to_str / big_int_from_str         串转换 (service_funcs.h)
 *   - big_int_gcd                              数论类 (number_theory.h)
 *
 * 编译: cmake 驱动，链接 libbig_int::libbig_int
 * 运行: 直接执行可执行文件，退出码 0 = 全部断言通过
 */
#include <stdio.h>
#include <string.h>
#include "big_int_full.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { printf("FAIL: %s\n", msg); failures++; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

int main(void) {
    printf("libbig_int consumer test start\n");
    printf("big_int_version=%s\n", big_int_version());

    big_int *a = big_int_create(4);
    big_int *b = big_int_create(4);
    big_int *r = big_int_create(8);
    big_int_str *s = big_int_str_create(64);
    int v = 0, rc = 0;

    /* 12345 + 6789 = 19134 */
    rc = big_int_from_int(12345, a);
    CHECK(rc == 0, "big_int_from_int(12345)");
    rc = big_int_from_int(6789, b);
    CHECK(rc == 0, "big_int_from_int(6789)");
    rc = big_int_add(a, b, r);
    CHECK(rc == 0, "big_int_add");
    big_int_clear_zeros(r);  /* 规范化长度后再导出 */
    rc = big_int_to_int(r, &v);
    CHECK(rc == 0 && v == 19134, "12345 + 6789 == 19134 (to_int)");

    /* 12345 * 6789 = 83810205 */
    rc = big_int_mul(a, b, r);
    CHECK(rc == 0, "big_int_mul");
    big_int_clear_zeros(r);
    rc = big_int_to_int(r, &v);
    CHECK(rc == 0 && v == 83810205, "12345 * 6789 == 83810205");

    /* 83810205 / 12345 = 6789 */
    rc = big_int_div(r, a, b);
    CHECK(rc == 0, "big_int_div");
    big_int_clear_zeros(b);
    rc = big_int_to_int(b, &v);
    CHECK(rc == 0 && v == 6789, "83810205 / 12345 == 6789");

    /* 十进制串往返: to_str -> from_str */
    rc = big_int_from_int(987654321, a);
    CHECK(rc == 0, "big_int_from_int(987654321)");
    rc = big_int_to_str(a, 10, s);
    CHECK(rc == 0, "big_int_to_str(base=10)");
    CHECK(strcmp((char *)s->str, "987654321") == 0, "to_str == \"987654321\"");
    rc = big_int_from_str(s, 10, b);
    CHECK(rc == 0, "big_int_from_str(base=10)");
    rc = big_int_to_int(b, &v);
    CHECK(rc == 0 && v == 987654321, "str round-trip == 987654321");

    /* gcd(1071, 462) = 21 */
    rc = big_int_from_int(1071, a);
    rc = big_int_from_int(462, b);
    rc = big_int_gcd(a, b, r);
    CHECK(rc == 0, "big_int_gcd");
    rc = big_int_to_int(r, &v);
    CHECK(rc == 0 && v == 21, "gcd(1071,462) == 21");

    big_int_destroy(a);
    big_int_destroy(b);
    big_int_destroy(r);
    big_int_str_destroy(s);

    if (failures == 0) {
        printf("libbig_int consumer test: OK (all checks passed)\n");
        return 0;
    }
    printf("libbig_int consumer test: %d FAILURES\n", failures);
    return 1;
}