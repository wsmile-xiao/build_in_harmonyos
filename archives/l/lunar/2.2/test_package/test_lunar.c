/*
 * test_lunar.c — lunar 2.2 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 设计要点（与本仓库 test_package 判据规范一致）：
 *   1) 全程不落盘：用 popen 内存管道直读子进程输出，绝不写 /tmp。
 *      OHOS 上 /tmp 是只读文件系统，任何"先重定向到 /tmp 再 grep"的判据
 *      都会与被测程序无关地失败。
 *   2) 跑不起来的完整分类：pclose==-1 / !WIFEXITED（被信号杀死）/
 *      WEXITSTATUS ∈ {126,127} 或 >= 128 一律判 FAIL。
 *      ★ 必须判 >=128：popen 经 /bin/sh 中转，shell 把信号死亡转写成
 *        128+signum（SIGSEGV→139、SIGABRT→134），只列 {126,127,255} 会漏掉
 *        最常见的段错误。
 *   3) 循环读到 EOF 再 pclose：单次 fread 后立刻 pclose 会让输出超过缓冲的
 *      子进程收到 SIGPIPE（假通过）或阻塞死锁。
 *   4) 用显式 expect() 计数汇总，不用 assert()：NDEBUG（Release）下 assert
 *      会被整体编译掉，测试会静默变成永远通过的空壳。
 *   5) 断言字面量全部取自 lunar.c 源码与本包实测基线，不臆造。
 *
 * 用法: test_lunar <lunar 可执行文件路径> [<share/lunar 数据目录>]
 *   第二个参数用于 -b（bitmap）用例：lunar 以相对路径 "lunar.bitmap" 打开
 *   字形位图，需在数据目录内执行。
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static const char *g_data_dir = NULL;
static int g_pass = 0;
static int g_fail = 0;

/* ── 断言原语 ─────────────────────────────────────────────── */
static void expect(int cond, const char *what, const char *detail)
{
    if (cond) {
        g_pass++;
        printf("  [PASS] %s\n", what);
    } else {
        g_fail++;
        printf("  [FAIL] %s%s%s\n", what,
               detail && *detail ? " — " : "",
               detail && *detail ? detail : "");
    }
    fflush(stdout);
}

static void expect_contains(const char *label, const char *out,
                            const char *needle)
{
    if (strstr(out, needle) != NULL) {
        g_pass++;
        printf("  [PASS] %s: 输出含 \"%s\"\n", label, needle);
    } else {
        g_fail++;
        printf("  [FAIL] %s: 输出缺 \"%s\"\n", label, needle);
        printf("         实际输出: %.300s%s\n", out,
               strlen(out) > 300 ? " ..." : "");
    }
    fflush(stdout);
}

/*
 * 执行 "<bin> <args>" 并把 stdout+stderr 合并读进 buf。
 * 返回：
 *   >= 0  子进程自身退出码（已排除跑不起来的各种情况）
 *   -1    跑不起来：popen 失败 / pclose==-1 / 被信号杀死 / 退出码 126,127,>=128
 * 因此调用方只需比较期望的退出码，无需重复判断信号。
 */
static int run_capture(const char *args, char *buf, size_t cap)
{
    char cmd[4096];
    FILE *fp;
    size_t n = 0, got;
    int rc, killed, code;

    if (g_data_dir && *g_data_dir)
        snprintf(cmd, sizeof(cmd),
                 "cd \"%s\" && \"%s\" %s < /dev/null 2>&1",
                 g_data_dir, g_bin, args);
    else
        snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", g_bin, args);

    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp)
        return -1;

    /* 循环读到 EOF（理由见文件头第 3 点） */
    while (n < cap - 1 && (got = fread(buf + n, 1, cap - 1 - n, fp)) > 0)
        n += got;
    buf[n] = '\0';

    rc = pclose(fp);
    if (rc == -1)
        return -1;
    killed = !WIFEXITED(rc);
    code = killed ? -1 : WEXITSTATUS(rc);
    if (killed || code == 126 || code == 127 || code >= 128)
        return -1;
    return code;
}

/* 判定一次调用：退出码 + 若干必须出现的字面量 */
static void case_expect(const char *args, int want_rc,
                        const char *const *needles, int n_needles)
{
    static char buf[65536];
    int rc, i;

    printf("── lunar %s\n", args);
    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        g_fail++;
        printf("  [FAIL] 进程无法正常执行（pclose==-1 / 被信号杀死 / 126,127,>=128）\n");
        return;
    }

    {
        char label[256];
        snprintf(label, sizeof(label), "退出码 (期望 %d)", want_rc);
        if (rc == want_rc) {
            expect(1, label, "");
        } else {
            char d[64];
            snprintf(d, sizeof(d), "实际 %d", rc);
            expect(0, label, d);
        }
    }
    for (i = 0; i < n_needles; i++)
        expect_contains("内容", buf, needles[i]);
}

/* 从输出里抽取 "Solar : Y.M.D.H" 或 "Lunar : Y.M.D.H" 的四个数字 */
static int extract_date(const char *out, const char *tag,
                        int *y, int *m, int *d, int *h)
{
    const char *p = strstr(out, tag);
    if (!p)
        return 0;
    return sscanf(p + strlen(tag), " %d.%d.%d.%d", y, m, d, h) >= 3;
}

int main(int argc, char **argv)
{
    static const char *c_usage[] = { "Usage:" };
    static const char *c_2000[] = {
        "Lunar Version 2.2 (October 28, 2001)",
        "Solar : 2000.1.1.0",
        "Lunar : 1999.11.25.0",
        "ShengXiao: Rabbit",
        "GanZhi: Ji3-Mao3.Bing3-Zi3.Wu4-Wu3.Ren2-Zi3",
        "16.13.55.49",
        "BaZi (8-characters) according to 'Four Column Calculation'",
    };
    static const char *c_lower[] = { "Lunar : 1900.1.1.0", "ShengXiao: Mouse" };
    static const char *c_upper[] = { "Lunar : 2049.12.7.0", "ShengXiao: Snake" };
    static const char *c_cny2024[] = {
        "Solar : 2024.2.10.0", "Lunar : 2024.1.1.0", "ShengXiao: Dragon",
    };
    static const char *c_cny2025[] = { "Lunar : 2025.1.1.0", "ShengXiao: Snake" };
    static const char *c_inv1[] = { "Solar : 2000.2.5.0", "Lunar : 2000.1.1.0" };
    static const char *c_inv2[] = { "Solar : 2023.3.11.0", "Lunar : 2023.2.20.0" };
    static const char *c_leap1[] = {
        "Solar : 2023.4.10.0", "Lunar : 2023.2Leap.20.0", "ShengXiao: Rabbit",
    };
    static const char *c_leap2[] = {
        "Solar : 2023.3.22.0", "Lunar : 2023.2Leap.1.0",
    };
    static const char *c_daybound1[] = { "Lunar : 1991.1.2.23" };
    static const char *c_daybound2[] = { "Lunar : 1991.1.2.0" };
    static const char *c_month[] = { "Month out of range." };
    static const char *c_day[] = { "Day out of range." };
    static const char *c_year[] = { "Year out of range." };
    static const char *c_hanzi[] = { "2000", "1999" };

    static const int sweep[][3] = {
        { 1900, 1, 31 }, { 1955, 6, 15 }, { 1976, 9, 9 }, { 1984, 2, 2 },
        { 1997, 7, 1 }, { 2001, 10, 1 }, { 2008, 8, 8 }, { 2012, 12, 21 },
        { 2020, 1, 25 }, { 2024, 2, 10 }, { 2033, 5, 1 }, { 2049, 12, 31 },
    };
    static char buf[65536];
    int i;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <lunar-binary> [share/lunar-dir]\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    if (argc >= 3)
        g_data_dir = argv[2];

    printf("=== lunar 2.2 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);
    if (g_data_dir)
        printf("数据目录  : %s\n", g_data_dir);

    /* ── 1. 公历 → 农历基准换算 ── */
    case_expect("2000 1 1", 0, c_2000, 7);
    case_expect("1900 1 31", 0, c_lower, 2);   /* 支持区间的下界 */
    case_expect("2049 12 31", 0, c_upper, 2);  /* 支持区间的上界 */
    case_expect("2024 2 10", 0, c_cny2024, 3); /* 甲辰年正月初一 */
    case_expect("2025 1 29", 0, c_cny2025, 2); /* 乙巳年正月初一 */

    /* ── 2. 农历 → 公历反查 ── */
    case_expect("-i 2000 1 1", 0, c_inv1, 2);
    case_expect("-i 2023 2 20", 0, c_inv2, 2);

    /* ── 3. 闰月（run-yue）── */
    case_expect("-i -l 2023 2 20", 0, c_leap1, 3);
    case_expect("-i -l 2023 2 1", 0, c_leap2, 2);

    /* ── 4. 农历日起于 23:00（man page 明示的约定）── */
    case_expect("1991 2 15 23", 0, c_daybound1, 1);
    case_expect("1991 2 16 0", 0, c_daybound2, 1);

    /* ── 5. 汉字段输出（-h，GB 编码，数字仍为 ASCII）── */
    case_expect("-h 2000 1 1", 0, c_hanzi, 2);

    /* ── 6. 越界错误路径：必须是非 0 退出码 + 明确原因 ── */
    case_expect("2000 13 1", 1, c_month, 1);
    case_expect("2000 1 32", 1, c_day, 1);
    case_expect("1800 1 1", 1, c_year, 1);

    /* ── 7. 用法/参数错误 ── */
    case_expect("", 1, c_usage, 1);
    case_expect("2000 1", 1, c_usage, 1);
    case_expect("-z 2000 1 1", 1, c_usage, 1);

    /* ── 8. 属性测试：公历→农历→公历 必须回到原点 ──
     *    不依赖硬编码对照表，遍历跨越整个支持区间的 12 个日期；
     *    闰月日期（月名带 Leap）跳过——反查需要额外的 -l 标志，
     *    已在上面的闰月用例单独覆盖。 */
    printf("── 往返一致性（solar → lunar → solar，%d 个采样点）\n",
           (int)(sizeof(sweep) / sizeof(sweep[0])));
    for (i = 0; i < (int)(sizeof(sweep) / sizeof(sweep[0])); i++) {
        char args[128], label[128];
        int y, mo, d, ly, lm, ld, lh, back_y, back_m, back_d, back_h;
        char leappos[512];
        const char *lp;

        snprintf(args, sizeof(args), "%d %d %d", sweep[i][0], sweep[i][1],
                 sweep[i][2]);
        if (run_capture(args, buf, sizeof(buf)) < 0) {
            snprintf(label, sizeof(label), "往返 %s: 首次调用失败", args);
            expect(0, label, "");
            continue;
        }
        if (!extract_date(buf, "Lunar :", &ly, &lm, &ld, &lh)) {
            snprintf(label, sizeof(label), "往返 %s: 无法解析农历行", args);
            expect(0, label, "");
            continue;
        }

        /* 闰月检测：农历行 "Lunar : 2023.2Leap.20.0" */
        snprintf(leappos, sizeof(leappos), "Lunar : %d.", ly);
        lp = strstr(buf, leappos);
        if (lp && strstr(lp, "Leap") && (strstr(lp, "Leap") - lp) < 40) {
            snprintf(label, sizeof(label), "往返 %s: 闰月，跳过", args);
            printf("  [SKIP] %s\n", label);
            continue;
        }

        snprintf(args, sizeof(args), "-i %d %d %d", ly, lm, ld);
        if (run_capture(args, buf, sizeof(buf)) < 0) {
            snprintf(label, sizeof(label), "往返 %d.%d.%d: 反查调用失败",
                     ly, lm, ld);
            expect(0, label, "");
            continue;
        }
        if (!extract_date(buf, "Solar :", &back_y, &back_m, &back_d, &back_h)) {
            snprintf(label, sizeof(label), "往返 %d.%d.%d: 无法解析公历行",
                     ly, lm, ld);
            expect(0, label, "");
            continue;
        }
        y = sweep[i][0]; mo = sweep[i][1]; d = sweep[i][2];
        {
            char what[160], detail[96];
            snprintf(what, sizeof(what),
                     "往返 %04d.%02d.%02d → 农历 %d.%d.%d → %04d.%02d.%02d",
                     y, mo, d, ly, lm, ld, back_y, back_m, back_d);
            snprintf(detail, sizeof(detail), "期望 %04d.%02d.%02d，实际 %04d.%02d.%02d",
                     y, mo, d, back_y, back_m, back_d);
            expect(back_y == y && back_m == mo && back_d == d, what,
                   (back_y == y && back_m == mo && back_d == d) ? "" : detail);
        }
    }

    /* ── 9. -b bitmap 输出（需要 share/lunar/lunar.bitmap）── */
    if (g_data_dir) {
        printf("── lunar -b 2000 1 1（bitmap 字形，需 lunar.bitmap）\n");
        if (run_capture("-b 2000 1 1", buf, sizeof(buf)) < 0) {
            expect(0, "-b 调用未正常执行", "");
        } else {
            expect(strstr(buf, "not found") == NULL,
                    "-b 能找到 lunar.bitmap 数据文件",
                    strstr(buf, "not found") ? "报 'not found'，数据文件未随包安装" : "");
            expect(strlen(buf) > 32, "-b 产出非空位图输出", "");
        }
    } else {
        printf("── 未提供数据目录，跳过 -b 用例\n");
    }

    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
