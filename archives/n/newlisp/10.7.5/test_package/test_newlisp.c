/* test_package/test_newlisp.c — newlisp 10.7.5 消费者冒烟 (R34)
 * 执行被测包二进制 newlisp，断言：
 *   newlisp -e '(+ 1 2)'  → 输出 3
 *   newlisp -v            → 输出含 10.7.5
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int check_arith(void) {
    FILE *fp = popen("newlisp -e '(+ 1 2)'", "r");
    if (fp == NULL) return 0;
    char buf[128];
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        pclose(fp);
        return 0;
    }
    pclose(fp);
    return strtol(buf, NULL, 10) == 3;
}

static int check_version(void) {
    FILE *fp = popen("newlisp -v", "r");
    if (fp == NULL) return 0;
    char buf[256];
    if (fgets(buf, sizeof(buf), fp) == NULL) {
        pclose(fp);
        return 0;
    }
    pclose(fp);
    return strstr(buf, "10.7.5") != NULL;
}

int main(void) {
    if (!check_arith()) {
        fprintf(stderr, "FAIL: newlisp -e '(+ 1 2)' 输出不是 3\n");
        return 1;
    }
    if (!check_version()) {
        fprintf(stderr, "FAIL: newlisp -v 输出不含 10.7.5\n");
        return 1;
    }
    printf("newlisp smoke ok: arith=3, version=10.7.5\n");
    return 0;
}