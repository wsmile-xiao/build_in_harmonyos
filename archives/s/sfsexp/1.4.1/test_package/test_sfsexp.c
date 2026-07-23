/* test_sfsexp.c — sfsexp 消费者测试
 * 验证 sfsexp 库的 S-表达式解析、打印、列表操作、销毁等核心 API
 */
#include "sfsexp/sexp.h"
#include "sfsexp/sexp_ops.h"
#include <stdio.h>
#include <string.h>

int main(void) {
    /* 测试1: 基础解析 - 解析简单列表 */
    sexp_t *sx = parse_sexp("(a b c)", 7);
    if (sx == NULL) {
        printf("FAIL: parse_sexp returned NULL for valid expression\n");
        return 1;
    }

    /* 测试2: 列表长度 */
    int len = sexp_list_length(sx);
    if (len != 3) {
        printf("FAIL: list length expected 3, got %d\n", len);
        destroy_sexp(sx);
        return 1;
    }

    /* 测试3: 打印回字符串 */
    char buf[256];
    int ret = print_sexp(buf, sizeof(buf), sx);
    if (ret < 0) {
        printf("FAIL: print_sexp failed\n");
        destroy_sexp(sx);
        return 1;
    }
    /* 打印结果应包含 "(a b c)" */
    if (strstr(buf, "a") == NULL || strstr(buf, "b") == NULL || strstr(buf, "c") == NULL) {
        printf("FAIL: printed result missing elements: %s\n", buf);
        destroy_sexp(sx);
        return 1;
    }

    destroy_sexp(sx);

    /* 测试4: 嵌套列表解析 */
    sexp_t *nested = parse_sexp("((1 2) (3 4))", 13);
    if (nested == NULL) {
        printf("FAIL: parse_sexp returned NULL for nested expression\n");
        return 1;
    }
    int nested_len = sexp_list_length(nested);
    if (nested_len != 2) {
        printf("FAIL: nested list length expected 2, got %d\n", nested_len);
        destroy_sexp(nested);
        return 1;
    }
    destroy_sexp(nested);

    /* 测试5: 查找元素 */
    sexp_t *tofind = parse_sexp("(x (target) y)", 14);
    if (tofind == NULL) {
        printf("FAIL: parse_sexp returned NULL for find expression\n");
        return 1;
    }
    sexp_t *found = find_sexp("target", tofind);
    if (found == NULL) {
        printf("FAIL: find_sexp did not find 'target'\n");
        destroy_sexp(tofind);
        return 1;
    }
    destroy_sexp(tofind);

    printf("PASS: all sfsexp tests passed\n");
    return 0;
}
