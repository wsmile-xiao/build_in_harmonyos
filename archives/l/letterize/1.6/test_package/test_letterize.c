/*
 * test_letterize.c — letterize 1.6 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   1) 全程不落盘：popen 内存管道直读子进程输出，绝不写 /tmp
 *      （OHOS 上 /tmp 是只读文件系统）。
 *   2) 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *      一律 FAIL。★ 必须判 >=128：popen 经 /bin/sh 中转，信号死亡被转写成
 *      128+signum（SIGSEGV→139、SIGABRT→134）。
 *   3) 循环读到 EOF 再 pclose（否则超缓冲输出会 SIGPIPE/死锁）。
 *   4) expect() 计数而非 assert()（NDEBUG 下 assert 会被整体编译掉）。
 *
 * 判据核心是**两条不依赖硬编码词表的属性**：
 *   P1  每一行 mnemonics 的长度必须等于输入长度（逐位 1:1 映射）；
 *   P2  对每一位，输出字符要么等于输入字符（输入位不是 2-9，如 0/1/'-'），
 *       要么落在该数字键位的字母集合内（2→ABC 3→DEF 4→GHI 5→JKL 6→MNO
 *       7→PRS 8→TUV 9→XYZ）。
 * 加上若干实测基线（行数、首行），既覆盖词表过滤行为，又不把判据绑死在一份
 * 可能抄错的完整词表上。
 *
 * 用法: test_letterize <letterize 可执行文件路径>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static int g_pass = 0;
static int g_fail = 0;

/* 美式电话键盘：2→abc 3→def 4→ghi 5→jkl 6→mno 7→prs 8→tuv 9→xyz
 * （0 与 1 没有字母，letterize 原样透传）
 * ★ letterize 输出为**小写**，此处必须用小写集合；用大写会整体误判 */
static const char *g_keypad[10] = {
    "0", "1", "abc", "def", "ghi", "jkl", "mno", "prs", "tuv", "xyz"
};

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

static int run_capture(const char *args, char *buf, size_t cap)
{
    char cmd[4096];
    FILE *fp;
    size_t n = 0, got;
    int rc, killed, code;

    snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", g_bin, args);
    buf[0] = '\0';
    fp = popen(cmd, "r");
    if (!fp)
        return -1;
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

/* 统计非空行数 */
static int count_lines(const char *buf)
{
    int n = 0;
    const char *p = buf;
    while (*p) {
        const char *e = strchr(p, '\n');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        if (len > 0)
            n++;
        if (!e)
            break;
        p = e + 1;
    }
    return n;
}

/* 取第 idx 行（0 基，只计非空行）到 out */
static int get_line(const char *buf, int idx, char *out, size_t cap)
{
    int n = 0;
    const char *p = buf;
    while (*p) {
        const char *e = strchr(p, '\n');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        if (len > 0) {
            if (n == idx) {
                if (len >= cap)
                    len = cap - 1;
                memcpy(out, p, len);
                out[len] = '\0';
                return 1;
            }
            n++;
        }
        if (!e)
            break;
        p = e + 1;
    }
    return 0;
}

/* P1 + P2：逐位校验一行 */
static int line_ok(const char *line, const char *input, char *why, size_t whycap)
{
    size_t i, n = strlen(input);
    if (strlen(line) != n) {
        snprintf(why, whycap, "行 \"%s\" 长度 %zu ≠ 输入长度 %zu",
                 line, strlen(line), n);
        return 0;
    }
    for (i = 0; i < n; i++) {
        unsigned char in = (unsigned char)input[i];
        unsigned char out = (unsigned char)line[i];
        if (in >= '2' && in <= '9') {
            if (strchr(g_keypad[in - '0'], (int)out) == NULL) {
                snprintf(why, whycap,
                         "第 %zu 位：输入 '%c' 映射到 \"%s\"，输出却是 '%c'",
                         i, in, g_keypad[in - '0'], out);
                return 0;
            }
        } else if (out != in) {
            snprintf(why, whycap,
                     "第 %zu 位：非数字键输入 '%c' 应原样透传，输出却是 '%c'",
                     i, in, out);
            return 0;
        }
    }
    return 1;
}

/* 一次完整用例：退出码 + 非空行数 + 首行 + 逐行属性校验 */
static void case_check(const char *input, int want_lines, const char *want_first)
{
    static char buf[262144];
    char label[256], why[256], first[256];
    char args[512];
    int rc, lines, i, bad = 0, seen = 0;

    printf("── letterize \"%s\"\n", input);
    /* 输入作为单个 argv 传入（letterize 接受多参数，必须引号锁定） */
    snprintf(args, sizeof(args), "\"%s\"", input);
    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "进程无法正常执行（pclose==-1 / 被信号杀死 / 126,127,>=128）", "");
        return;
    }
    {
        char d[64];
        snprintf(label, sizeof(label), "退出码 (期望 0)");
        snprintf(d, sizeof(d), "实际 %d", rc);
        expect(rc == 0, label, rc == 0 ? "" : d);
    }

    lines = count_lines(buf);
    {
        char d[96];
        snprintf(label, sizeof(label), "非空行数 (期望 %d)", want_lines);
        snprintf(d, sizeof(d), "实际 %d", lines);
        expect(lines == want_lines, label, lines == want_lines ? "" : d);
    }

    if (want_first) {
        if (get_line(buf, 0, first, sizeof(first))) {
            char d[320];
            snprintf(label, sizeof(label), "首行 (期望 \"%s\")", want_first);
            snprintf(d, sizeof(d), "实际 \"%s\"", first);
            expect(strcmp(first, want_first) == 0, label,
                   strcmp(first, want_first) == 0 ? "" : d);
        } else {
            expect(0, "至少产出一行", "输出为空");
        }
    }

    /* P1 + P2 属性：逐行逐位校验 */
    for (i = 0; i < lines; i++) {
        if (!get_line(buf, i, first, sizeof(first)))
            continue;
        seen++;
        if (!line_ok(first, input, why, sizeof(why))) {
            if (!bad) {
                snprintf(label, sizeof(label), "逐位映射属性 (P1/P2) 全部行成立");
                expect(0, label, why);
            }
            bad++;
        }
    }
    if (!bad) {
        char d[96];
        snprintf(label, sizeof(label), "逐位映射属性 (P1/P2) 全部 %d 行成立", seen);
        snprintf(d, sizeof(d), "");
        expect(seen > 0, label, "");
    }
}

int main(int argc, char **argv)
{
    static char buf[262144];
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <letterize-binary>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];

    printf("=== letterize 1.6 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);

    /* ── 1. 实测基线：行数 + 首行 + 属性 ── */
    case_check("234", 13, "adg");
    case_check("2275", 19, "aarj");
    case_check("5551234", 78, "jjj1adg");
    case_check("5551234567", 246, "jjj1adgkop");
    case_check("12", 3, "1a");

    /* ── 2. 非数字键位原样透传 ── */
    case_check("0000000", 1, "0000000");
    case_check("1-800-555", 18, "1-t00-jjj");
    case_check("1", 1, "1");

    /* ── 3. 空输入：无输出、退出码 0 ── */
    printf("── letterize（无参数）\n");
    rc = run_capture("", buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "空输入调用无法正常执行", "");
    } else {
        char d[64];
        snprintf(d, sizeof(d), "实际 %d", rc);
        expect(rc == 0, "空输入退出码 (期望 0)", rc == 0 ? "" : d);
        expect(count_lines(buf) == 0, "空输入无输出", "");
    }

    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
