// ohos_special_test.c — clove-unit 2.4.6 鸿蒙（OHOS）专项测试
//
// 独立于 test.c（消费者冒烟，3 用例 / 8 断言）的 HarmonyOS 端到端专项用例：
// 通过 popen 逐模式驱动本 test_package 自己编出来的消费者可执行文件
// `test_clove_unit`（路径由 CTest 以 $<TARGET_FILE:> 传入），在 OHOS aarch64
// 目标上真实断言 clove 的关键能力：
//   * 测试自动发现 —— runner 走 dl_iterate_phdr + ELF SHT_SYMTAB 符号表扫描，
//     在 OHOS 目标上必须真能发现 3 条用例（假发现会表现为 Total: 0）；
//   * 三种报告格式（pretty / csv / json）的字段与计数；
//   * -i / -e 过滤语义与 -x 非零退出语义；
//   * -h / -v 自报版本与上游 2.4.6 一致。
// 共 16 项断言；每项都要求可观察结果，非空壳。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *g_exe = NULL;
static int g_checks = 0;
static int g_failures = 0;

/* 运行 "<exe> <args> 2>&1"，stdout+stderr 捕获进 buf，返回 pclose 状态（-1=起不来） */
static int run_capture(const char *args, char *buf, size_t bufsz)
{
    char cmd[1024];
    int n = snprintf(cmd, sizeof(cmd), "%s %s 2>&1", g_exe, args);
    if (n < 0 || (size_t)n >= sizeof(cmd)) {
        return -1;
    }
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        buf[0] = '\0';
        return -1;
    }
    size_t got = fread(buf, 1, bufsz - 1, fp);
    buf[got] = '\0';
    return pclose(fp);
}

/* pclose 返回的是 wait(2) 状态字：取退出码 */
static int exit_code(int pclose_status)
{
    if (pclose_status < 0) {
        return -1;
    }
    if (WIFEXITED(pclose_status)) {
        return WEXITSTATUS(pclose_status);
    }
    return -1;
}

static void check(int cond, const char *what)
{
    g_checks++;
    if (!cond) {
        g_failures++;
        fprintf(stderr, "OHOS-SPECIAL FAIL: %s\n", what);
    }
}

static void strip_trailing_nl(char *s)
{
    size_t n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r')) {
        s[--n] = '\0';
    }
}

int main(int argc, char *argv[])
{
    char out[65536];
    int st;

    if (argc < 2) {
        fprintf(stderr, "usage: ohos_special_test <path/to/test_clove_unit>\n");
        return 2;
    }
    g_exe = argv[1];

    /* 1) 默认模式：ELF 符号表自动发现必须真发现 3 条用例并全过 */
    st = run_capture("", out, sizeof(out));
    check(exit_code(st) == 0, "默认模式退出码应为 0");
    check(strstr(out, "Suites / Tests found: 1 / 3") != NULL,
          "自动发现应为 1 suite / 3 tests（符号表扫描在 OHOS 目标上生效）");
    check(strstr(out, "Total: 3, Passed: 3, Failed: 0, Skipped: 0") != NULL,
          "默认模式应 3/3 全过");
    check(strstr(out, "Run result: SUCCESS") != NULL, "默认模式应报 SUCCESS");

    /* 2) -x：失败才非零退出，全过时退出码必须为 0 */
    st = run_capture("-x", out, sizeof(out));
    check(exit_code(st) == 0, "-x 模式全过时退出码应为 0");

    /* 3) -l：列表模式逐条列出用例名 */
    st = run_capture("-l", out, sizeof(out));
    check(strstr(out, "Listing 3 Test(s) in 1 Suite(s)") != NULL,
          "-l 应列出 3 条用例 / 1 个 suite");
    /* -l 的形态是「Suite (file: ...)」换行后「- TestName [line: N]」，不是 Suite.Test */
    check(strstr(out, "ConsumerSmoke (file:") != NULL
              && strstr(out, "- IntArithmetic [line:") != NULL,
          "-l 应列出 suite ConsumerSmoke 与其用例 - IntArithmetic");

    /* 4) -r csv：表头与数据行 */
    st = run_capture("-r csv", out, sizeof(out));
    check(strncmp(out, "Suite,Test,Status,Duration", 26) == 0,
          "csv 首行应为 Suite,Test,Status,Duration,...");
    check(strstr(out, "ConsumerSmoke,IntArithmetic,PASS") != NULL,
          "csv 应含 ConsumerSmoke,IntArithmetic,PASS 数据行");

    /* 5) -r json：计数与版本字段 */
    st = run_capture("-r json", out, sizeof(out));
    check(strstr(out, "\"test_count\" : 3") != NULL, "json 应含 test_count = 3");
    check(strstr(out, "\"test_passed\" : 3") != NULL, "json 应含 test_passed = 3");
    check(strstr(out, "\"clove_version\" : \"2.4.6\"") != NULL,
          "json 应自报 clove_version = 2.4.6");

    /* 6) -i / -e 过滤语义 */
    st = run_capture("-i ConsumerSmoke.StringHandling", out, sizeof(out));
    check(strstr(out, "Total: 1, Passed: 1") != NULL, "-i 过滤后应只剩 1 条");
    st = run_capture("-e ConsumerSmoke.StringHandling", out, sizeof(out));
    check(strstr(out, "Total: 2, Passed: 2") != NULL, "-e 排除后应剩 2 条");

    /* 7) -v / -h 自报版本与上游 tag 一致 */
    st = run_capture("-v", out, sizeof(out));
    strip_trailing_nl(out);
    check(strcmp(out, "2.4.6") == 0, "-v 应输出 2.4.6");
    st = run_capture("-h", out, sizeof(out));
    check(strstr(out, "CLove-Unit v2.4.6") != NULL, "-h 应输出 CLove-Unit v2.4.6");

    if (g_failures) {
        fprintf(stderr, "OHOS-SPECIAL: %d/%d check(s) failed\n", g_failures, g_checks);
        return 1;
    }
    printf("OHOS-SPECIAL: clove-unit 2.4.6 ok (%d checks: autodiscovery/pretty/csv/json/"
           "filter/version on OHOS aarch64)\n", g_checks);
    return 0;
}
