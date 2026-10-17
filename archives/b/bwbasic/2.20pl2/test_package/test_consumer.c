/* bwbasic 2.20pl2 消费者测试驱动：
 * 用包内 bwbasic 二进制执行内嵌 BASIC 程序，断言：
 *   1) 算术（MUL= 42）
 *   2) 关系分支（LT-OK）
 *   3) 数组与浮点（V= 1.5000000）
 *   4) 无效下标触发解释器 ERROR（反例）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_case(const char *bwbasic, const char *prog, const char *code,
                    const char *expect) {
    char cmd[4096];
    char out[8192];
    size_t n;
    int rc;

    FILE *f = fopen(prog, "w");
    if (!f) {
        fprintf(stderr, "FAIL: cannot write %s\n", prog);
        return 1;
    }
    fputs(code, f);
    fclose(f);

    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null", bwbasic, prog);
    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: popen\n");
        return 1;
    }
    n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    rc = pclose(p);

    if (rc != 0) {
        fprintf(stderr, "FAIL: interpreter exit %d\n", rc);
        return 1;
    }
    if (!strstr(out, expect)) {
        fprintf(stderr, "FAIL: expected <%s> in interpreter output\n", expect);
        return 1;
    }
    return 0;
}

static int run_err_case(const char *bwbasic, const char *prog, const char *code) {
    char cmd[4096];
    char out[8192];
    size_t n;

    FILE *f = fopen(prog, "w");
    if (!f) {
        fprintf(stderr, "FAIL: cannot write %s\n", prog);
        return 1;
    }
    fputs(code, f);
    fclose(f);

    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null", bwbasic, prog);
    FILE *p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: popen\n");
        return 1;
    }
    n = fread(out, 1, sizeof(out) - 1, p);
    out[n] = '\0';
    pclose(p);

    if (!strstr(out, "ERROR")) {
        fprintf(stderr, "FAIL: invalid subscript did not raise interpreter ERROR\n");
        return 1;
    }
    return 0;
}

int main(int argc, char **argv) {
    int fails = 0;
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-bwbasic>\n", argv[0]);
        return 2;
    }

    if (run_case(argv[1], "consumer_mul.bas",
                 "10 LET A = 6\n20 LET B = 7\n30 PRINT \"MUL=\"; A * B\n40 END\n",
                 "MUL= 42")) {
        fails++;
    }
    if (run_case(argv[1], "consumer_lt.bas",
                 "10 IF 3 < 5 THEN PRINT \"LT-OK\"\n20 END\n",
                 "LT-OK")) {
        fails++;
    }
    if (run_case(argv[1], "consumer_arr.bas",
                 "10 DIM V(3)\n20 V(1) = 1.5\n30 PRINT \"V=\"; V(1)\n40 END\n",
                 "V= 1.5000000")) {
        fails++;
    }
    if (run_err_case(argv[1], "consumer_err.bas",
                     "10 DIM N(5)\n20 PRINT N(7)\n30 END\n")) {
        fails++;
    }

    remove("consumer_mul.bas");
    remove("consumer_lt.bas");
    remove("consumer_arr.bas");
    remove("consumer_err.bas");

    if (fails) {
        fprintf(stderr, "%d consumer check(s) failed\n", fails);
        return 1;
    }
    printf("bwbasic consumer test PASSED: arithmetic, relational branch, "
           "array/float execution and invalid-subscript error path (4 checks)\n");
    return 0;
}
