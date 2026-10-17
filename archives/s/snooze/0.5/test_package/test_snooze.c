/*
 * test_snooze.c — snooze 0.5 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   - popen 内存管道直读，**不使用 /tmp**（OHOS 上只读）
 *   - 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *     一律判 FAIL（popen 经 /bin/sh 中转，信号死亡被转写成 128+signum）
 *   - 循环读到 EOF 再 pclose；expect() 计数而非 assert()
 *
 * ★ 关键设计：**只测 -n 干跑模式，绝不进入真实等待**。
 *   snooze 的常规模式会 sleep 到下一个匹配时刻才返回（消费级测试里必然挂起），
 *   因此所有用例都带 `-n`；这也让判据完全不依赖当前时刻。
 *
 * ★ 时间无关的判据主体（不硬编码任何时间戳）：
 *   P1  干跑恰好输出 5 行（上游 -n 的定义）；
 *   P2  每行形状为 `YYYY-MM-DDTHH:MM:SS[+-]ZZZZ Ddd ...`；
 *   P3  5 个时刻严格递增；
 *   P4  行内星期缩写与日期**自洽**（用 days_from_civil 独立算出星期，与打印值比对）；
 *   P5  每行的时间字段满足所请求的日期/时间模式（-H/-M/-d/-w/-D 约束）；
 *   P6  -J 的抖动后缀精确出现在每行末尾。
 *   P3/P4 让判据不依赖系统时间，也不依赖外部历法表——被测程序自己证明自己的
 *   日期算术与星期换算自洽。
 *
 * 用法: test_snooze <snooze 可执行文件路径>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static int g_pass = 0, g_fail = 0;

/* 解析出的一行时刻 */
struct dt {
    int y, mo, d, h, mi, s;
    char wday[8];
    int wd;            /* 0=Sunday .. 6=Saturday（由日期独立算出） */
    long long abs;     /* 自 1970-01-01 起的秒数，用于递增判断 */
    char tail[128];    /* 相对时间字段之后的所有内容 */
};

static void expect(int cond, const char *what, const char *detail)
{
    if (cond) {
        g_pass++;
        printf("  [PASS] %s\n", what);
    } else {
        g_fail++;
        printf("  [FAIL] %s%s%s\n", what,
               detail && *detail ? " — " : "", detail && *detail ? detail : "");
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

/* Howard Hinnant: days from civil (1970-01-01 为 0) */
static long long days_from_civil(int y, unsigned m, unsigned d)
{
    long long yy = y;
    yy -= m <= 2;
    long long era = (yy >= 0 ? yy : yy - 399) / 400;
    unsigned yoe = (unsigned)(yy - era * 400);
    unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (long long)doe - 719468;
}

static int is_leap(int y)
{
    return (y % 4 == 0 && y % 100 != 0) || y % 400 == 0;
}

static int day_of_year(int y, int m, int d)
{
    static const int cum[12] = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 };
    int doy = cum[m - 1] + d;
    if (m > 2 && is_leap(y))
        doy++;
    return doy;
}

/* 解析一行：`2026-09-19T00:00:00+0800 Sat  0d 19h 23m  9s [suffix]` */
static int parse_line(const char *ln, struct dt *t)
{
    const char *p;
    size_t len = strlen(ln);

    if (len < 34)
        return 0;
    if (sscanf(ln, "%4d-%2d-%2dT%2d:%2d:%2d", &t->y, &t->mo, &t->d,
               &t->h, &t->mi, &t->s) != 6)
        return 0;
    if (ln[4] != '-' || ln[7] != '-' || ln[10] != 'T' || ln[13] != ':' ||
        ln[16] != ':' || (ln[19] != '+' && ln[19] != '-') || ln[24] != ' ')
        return 0;
    {
        int i;
        for (i = 20; i <= 23; i++)
            if (!isdigit((unsigned char)ln[i]))
                return 0;
    }
    if (!isalpha((unsigned char)ln[25]) || !isalpha((unsigned char)ln[26]) ||
        !isalpha((unsigned char)ln[27]))
        return 0;
    memcpy(t->wday, ln + 25, 3);
    t->wday[3] = '\0';

    /* 相对时间字段（"0d 19h 23m  9s" 之类）从第 29 字节开始 */
    p = ln + 28;
    while (*p == ' ')
        p++;
    snprintf(t->tail, sizeof(t->tail), "%s", p);

    t->abs = days_from_civil(t->y, (unsigned)t->mo, (unsigned)t->d) * 86400LL
             + t->h * 3600 + t->mi * 60 + t->s;
    t->wd = (int)(((days_from_civil(t->y, (unsigned)t->mo, (unsigned)t->d) % 7) + 7 + 4) % 7);
    return 1;
}

static void check_wday_name(struct dt *t)
{
    static const char *NAMES[7] = { "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat" };
    char label[160], d[128];
    int ok = (strcmp(t->wday, NAMES[t->wd]) == 0);
    snprintf(label, sizeof(label),
             "星期自洽 %04d-%02d-%02d：打印 %s / 独立计算 %s",
             t->y, t->mo, t->d, t->wday, NAMES[t->wd]);
    snprintf(d, sizeof(d), "不一致（打印 %s，应为 %s）", t->wday, NAMES[t->wd]);
    expect(ok, label, ok ? "" : d);
}

/* 把 buf 切成最多 8 行（去空行） */
static int split_lines(const char *buf, char lines[][256], int max)
{
    int n = 0;
    const char *p = buf;
    while (*p && n < max) {
        const char *e = strchr(p, '\n');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        if (len > 0) {
            if (len > 255)
                len = 255;
            memcpy(lines[n], p, len);
            lines[n][len] = '\0';
            n++;
        }
        if (!e)
            break;
        p = e + 1;
    }
    return n;
}

/* 干跑用例：断言 5 行 + 形状 + 递增 + 星期自洽 + 自定义约束 */
struct ctx {
    const char *tag;
    int want_lines;
    /* 期望约束，-1 表示不约束 */
    int h, mi, d, wlo, whi;   /* wlo/whi 为允许的星期集合（0..6）；wlo<0 表示不约束 */
    int wmask;                /* 位掩码，替代 wlo/whi */
    int use_wmask;
    int doy[4], n_doy;        /* 允许的 day-of-year 集合 */
    int mi_set[8], n_mi_set;  /* 允许的分钟集合（列表语法用） */
};

static void case_dry(const struct ctx *c)
{
    static char buf[65536];
    static char lines[16][256];
    struct dt t, prev;
    char label[256], d[192], args[1024];
    int rc, n, i, ok, bad = 0;

    snprintf(args, sizeof(args), "-n %s", c->tag);
    printf("── snooze %s\n", args);

    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "进程无法正常执行（pclose==-1 / 被信号杀死 / 126,127,>=128）", "");
        return;
    }
    snprintf(label, sizeof(label), "退出码 (期望 0)");
    expect(rc == 0, label, rc == 0 ? "" : "非 0");

    n = split_lines(buf, lines, 16);
    snprintf(label, sizeof(label), "行数 (期望 %d)", c->want_lines);
    snprintf(d, sizeof(d), "实际 %d", n);
    expect(n == c->want_lines, label, n == c->want_lines ? "" : d);
    if (n <= 0)
        return;

    /* P2 形状 + P3 递增 + P4 星期自洽 */
    for (i = 0; i < n; i++) {
        if (!parse_line(lines[i], &t)) {
            snprintf(label, sizeof(label), "第 %d 行形状合法 (YYYY-MM-DDTHH:MM:SS+ZZZZ Ddd …)", i + 1);
            snprintf(d, sizeof(d), "实际 \"%s\"", lines[i]);
            expect(0, label, d);
            bad++;
            continue;
        }
        if (i > 0 && t.abs <= prev.abs) {
            snprintf(label, sizeof(label), "第 %d 行严格晚于第 %d 行", i + 1, i);
            expect(0, label, "未严格递增");
            bad++;
        } else if (i > 0) {
            snprintf(label, sizeof(label), "第 %d 行严格晚于第 %d 行", i + 1, i);
            expect(1, label, "");
        }
        check_wday_name(&t);

        /* P5 字段约束 */
        if (c->h >= 0) {
            ok = (t.h == c->h);
            snprintf(label, sizeof(label), "第 %d 行小时 == %02d", i + 1, c->h);
            snprintf(d, sizeof(d), "实际 %02d", t.h);
            expect(ok, label, ok ? "" : d);
        }
        if (c->mi >= 0) {
            ok = (t.mi == c->mi);
            snprintf(label, sizeof(label), "第 %d 行分钟 == %02d", i + 1, c->mi);
            snprintf(d, sizeof(d), "实际 %02d", t.mi);
            expect(ok, label, ok ? "" : d);
        }
        if (c->d >= 0) {
            ok = (t.d == c->d);
            snprintf(label, sizeof(label), "第 %d 行日 == %02d", i + 1, c->d);
            snprintf(d, sizeof(d), "实际 %02d", t.d);
            expect(ok, label, ok ? "" : d);
        }
        if (c->use_wmask) {
            ok = ((c->wmask >> t.wd) & 1) != 0;
            snprintf(label, sizeof(label), "第 %d 行星期在允许集合内 (%s)", i + 1, t.wday);
            expect(ok, label, ok ? "" : "不在集合内");
        }
        if (c->n_doy > 0) {
            int doy = day_of_year(t.y, t.mo, t.d), j, hit = 0;
            for (j = 0; j < c->n_doy; j++)
                if (c->doy[j] == doy)
                    hit = 1;
            ok = hit;
            snprintf(label, sizeof(label), "第 %d 行年积日 ∈ 集合 (实际 %d, %04d-%02d-%02d)",
                     i + 1, doy, t.y, t.mo, t.d);
            expect(ok, label, ok ? "" : "不在集合内");
        }
        if (c->n_mi_set > 0) {
            int j, hit = 0;
            for (j = 0; j < c->n_mi_set; j++)
                if (c->mi_set[j] == t.mi)
                    hit = 1;
            ok = hit;
            snprintf(label, sizeof(label), "第 %d 行分钟 ∈ 列表集合 (实际 %02d)", i + 1, t.mi);
            expect(ok, label, ok ? "" : "不在集合内");
        }
        prev = t;
    }
    printf("  （本用例 %d 项未通过）\n", bad);
}

/* 非法模式用例 */
static void case_error(const char *tag, const char *want_msg)
{
    static char buf[16384];
    char args[512], label[256];
    int rc;

    snprintf(args, sizeof(args), "-n %s echo hi", tag);
    printf("── snooze %s\n", args);
    rc = run_capture(args, buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "进程无法正常执行", "");
        return;
    }
    snprintf(label, sizeof(label), "退出码 (期望 1)");
    expect(rc == 1, label, rc == 1 ? "" : "非 1");
    snprintf(label, sizeof(label), "报错含 \"%s\"", want_msg);
    expect(strstr(buf, want_msg) != NULL, label, strstr(buf, want_msg) ? "" : "未出现");
}

int main(int argc, char **argv)
{
    static char buf[16384];
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <snooze-binary>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    printf("=== snooze 0.5 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);

    /* ── 1. 时间模式约束（时间无关：只校验字段，不校验具体时刻）── */
    {
        struct ctx c;
        memset(&c, 0, sizeof(c));
        c.tag = "-H 0 -M 0 echo hi";
        c.want_lines = 5; c.h = 0; c.mi = 0; c.d = -1;
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-M 5 -- echo hi";
        c.want_lines = 5; c.h = -1; c.mi = 5; c.d = -1;
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-d 1 -H 14 -M 15 echo hi";
        c.want_lines = 5; c.h = 14; c.mi = 15; c.d = 1;
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-w 1-5 -H 22 echo hi";
        c.want_lines = 5; c.h = 22; c.mi = -1; c.d = -1;
        c.use_wmask = 1; c.wmask = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5);
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-w 0,6 -H 12 echo hi";
        c.want_lines = 5; c.h = 12; c.mi = -1; c.d = -1;
        c.use_wmask = 1; c.wmask = (1 << 0) | (1 << 6);
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-M 1,3,5 echo hi";     /* 列表语法：分钟只能是 1/3/5 之一 */
        c.want_lines = 5; c.h = -1; c.mi = -1; c.d = -1;
        c.mi_set[0] = 1; c.mi_set[1] = 3; c.mi_set[2] = 5; c.n_mi_set = 3;
        case_dry(&c);

        memset(&c, 0, sizeof(c));
        c.tag = "-D 1,100,200 -H 3 echo hi";
        c.want_lines = 5; c.h = 3; c.mi = -1; c.d = -1;
        c.doy[0] = 1; c.doy[1] = 100; c.doy[2] = 200; c.n_doy = 3;
        case_dry(&c);
    }

    /* ── 2. 无任何时间模式：默认午夜每日 ── */
    {
        struct ctx c;
        memset(&c, 0, sizeof(c));
        c.tag = "echo hi";              /* -n echo hi */
        c.want_lines = 5; c.h = 0; c.mi = 0; c.d = -1;
        case_dry(&c);
    }

    /* ── 3. 非法模式：必须非 0 退出码 + 明确范围 ── */
    case_error("-H 99", "number outside 0 <= n < 24");
    case_error("-M 60", "number outside 0 <= n < 60");
    case_error("-w 8", "number outside 0 <= n < 8");
    case_error("-d 32", "number outside 1 <= n < 32");
    case_error("-m 13", "number outside 1 <= n < 13");
    case_error("-D 367", "number outside 1 <= n < 367");
    case_error("-W 54", "number outside 1 <= n < 54");

    /* ── 4. -J 抖动后缀精确出现（P6）── */
    printf("── snooze -n -J 30 -H 0 -M 0 echo hi\n");
    rc = run_capture("-n -J 30 -H 0 -M 0 echo hi", buf, sizeof(buf));
    if (rc < 0) {
        expect(0, "抖动用例无法执行", "");
    } else {
        static char lines[16][256];
        struct dt t;
        int n = split_lines(buf, lines, 16), i, all = 1;
        expect(n == 5, "抖动用例 5 行", "");
        for (i = 0; i < n; i++) {
            if (!parse_line(lines[i], &t) || strstr(t.tail, "(plus up to 30s for jitter)") == NULL)
                all = 0;
        }
        expect(all, "-J 30 每行都带 \"(plus up to 30s for jitter)\" 后缀", "");
    }

    /* ── 5. 无抖动时不应出现抖动后缀（负向对照）── */
    printf("── snooze -n -H 0 -M 0 echo hi（负向对照）\n");
    rc = run_capture("-n -H 0 -M 0 echo hi", buf, sizeof(buf));
    if (rc >= 0)
        expect(strstr(buf, "jitter") == NULL, "无 -J 时不出现 jitter 后缀", "");

    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
