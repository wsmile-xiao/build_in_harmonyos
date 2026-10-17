/*
 * test_spline.c — aspline (spline 1.2) 消费者侧测试（HarmonyOS PC / OHOS aarch64）
 *
 * 判据设计（与本仓库 test_package 规范一致）：
 *   - popen 内存管道直读，**不使用 /tmp**（OHOS 上只读）；输入数据写到 argv[2]
 *     传入的 scratch 目录，并先显式探测可写性
 *   - 跑不起来的完整分类：pclose==-1 / !WIFEXITED / 退出码 ∈ {126,127} 或 >=128
 *     一律判 FAIL（popen 经 /bin/sh 中转，信号死亡被转写成 128+signum）
 *   - 循环读到 EOF 再 pclose；expect() 计数而非 assert()
 *
 * ★ 判据主体是**自闭合属性**而非 golden 向量。aspline 的手册承诺
 *   "produces a similar set, which is approximately equally spaced and
 *    **includes the input set**"，由此得到两条不依赖期望表的判据：
 *     P1  输入点包含性——每个输入 (x,y) 都必须出现在输出中（手册明示契约）
 *     P2  常量保持性——输入所有 y 相同的常量函数，输出每一点 y 必须仍等于该常量
 *   另有结构性属性：输出 x 严格递增、输出行数不少于输入点数。
 *
 * 用法: test_spline <aspline 可执行文件路径> <可写 scratch 目录>
 */
#define _POSIX_C_SOURCE 200809L

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/wait.h>

static const char *g_bin = NULL;
static const char *g_scratch = NULL;
static int g_pass = 0, g_fail = 0;

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

static void expect_contains(const char *label, const char *out, const char *needle)
{
    char what[320], d[400];
    snprintf(what, sizeof(what), "%s: 输出含 \"%s\"", label, needle);
    if (strstr(out, needle) != NULL) {
        expect(1, what, "");
    } else {
        snprintf(d, sizeof(d), "实际输出: %.240s", out);
        expect(0, what, d);
    }
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

/* 把数据集写到 scratch 下的文件，返回路径 */
static const char *write_data(const char *name, const char *content)
{
    static char path[600];
    FILE *f;
    snprintf(path, sizeof(path), "%s/%s", g_scratch, name);
    f = fopen(path, "wb");
    if (!f)
        return NULL;
    fputs(content, f);
    fclose(f);
    return path;
}

/* 解析输出里的第 idx 行（0 基，非空），返回 x、y */
static int get_point(const char *buf, int idx, double *x, double *y)
{
    int n = 0;
    const char *p = buf;
    char line[256];
    while (*p) {
        const char *e = strchr(p, '\n');
        size_t len = e ? (size_t)(e - p) : strlen(p);
        if (len > 0 && len < sizeof(line)) {
            memcpy(line, p, len);
            line[len] = '\0';
            if (n == idx) {
                if (sscanf(line, "%lf %lf", x, y) != 2)
                    return 0;
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

int main(int argc, char **argv)
{
    static char buf[262144];
    char args[1024], label[320], d[320];
    const char *fp;
    int rc, i, lines;
    double x0, y0;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <aspline-binary> <scratch-dir>\n", argv[0]);
        return 2;
    }
    g_bin = argv[1];
    g_scratch = argv[2];
    printf("=== aspline (spline 1.2) 消费者测试 ===\n");
    printf("被测二进制: %s\n", g_bin);
    printf("scratch   : %s\n", g_scratch);

    /* ── 0. scratch 可写性显式探测 ── */
    fp = write_data("probe.tmp", "probe\n");
    if (!fp) {
        expect(0, "scratch 目录可写（探针文件写入成功）", g_scratch);
        goto summary;
    }
    expect(1, "scratch 目录可写（探针文件写入成功）", "");

    /* ── 1. 用法 / 版本 / 许可 ──
     *   ★ 实测：用法行里的程序名取自 **argv[0] 的 basename**（把二进制复制成
     *     别的名字，用法里就跟着变）。因此断言只取与程序名无关的选项规格部分。 */
    printf("── aspline -h\n");
    rc = run_capture("-h", buf, sizeof(buf));
    expect(rc == 0, "-h 退出码 (期望 0)", "");
    expect_contains("-h", buf, "[-hv][-a [xstep]][-l llimit][-u ulimit][-n points]");
    expect_contains("-h", buf, "{data-file(s)}");

    printf("── aspline --help\n");
    rc = run_capture("--help", buf, sizeof(buf));
    expect(rc == 0, "--help 退出码 (期望 0)", "");
    expect_contains("--help", buf, "usage:");
    expect_contains("--help", buf, "supply abscissas automatically");

    printf("── aspline -V\n");
    rc = run_capture("-V", buf, sizeof(buf));
    expect(rc == 0, "-V 退出码 (期望 0)", "");
    expect_contains("-V", buf, "version 1.2");
    expect_contains("-V", buf, "Akima spline interpolation");

    printf("── aspline --version\n");
    rc = run_capture("--version", buf, sizeof(buf));
    expect_contains("--version", buf, "version 1.2");

    printf("── aspline -W\n");
    rc = run_capture("-W", buf, sizeof(buf));
    expect(rc == 0, "-W 退出码 (期望 0)", "");
    expect_contains("-W", buf, "GNU General Public License");

    /* ── 2. 边界输入 ── */
    printf("── 空文件（无数据点）\n");
    fp = write_data("empty.txt", "");
    if (fp) {
        snprintf(args, sizeof(args), "\"%s\"", fp);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "空输入退出码 (期望 0)", "");
        expect(count_lines(buf) == 0, "空输入无输出", "");
    }

    printf("── 单点数据集\n");
    fp = write_data("single.txt", "1 1\n");
    if (fp) {
        snprintf(args, sizeof(args), "\"%s\"", fp);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "单点退出码 (期望 0)", "");
        if (get_point(buf, 0, &x0, &y0))
            expect(fabs(x0 - 1.0) < 1e-9 && fabs(y0 - 1.0) < 1e-9,
                   "单点原样输出 \"1 1\"", "");
        else
            expect(0, "单点原样输出 \"1 1\"", buf);
    }

    /* ── 3. P2 常量保持性：输入全为同一常量，输出必须处处等于该常量 ── */
    {
        static const double CONSTS[] = { 5.0, 0.0, -3.25 };
        int k;
        for (k = 0; k < 3; k++) {
            char content[512];
            double c = CONSTS[k];
            int j, bad = 0;
            snprintf(content, sizeof(content),
                     "0 %g\n1 %g\n2 %g\n3 %g\n4 %g\n", c, c, c, c, c);
            fp = write_data("const.txt", content);
            if (!fp)
                continue;
            snprintf(args, sizeof(args), "\"%s\"", fp);
            rc = run_capture(args, buf, sizeof(buf));
            snprintf(label, sizeof(label), "常量 y=%g：退出码 0", c);
            expect(rc == 0, label, "");
            lines = count_lines(buf);
            for (j = 0; j < lines; j++) {
                double x, y;
                if (!get_point(buf, j, &x, &y)) {
                    bad = 1;
                    break;
                }
                if (fabs(y - c) > 1e-9) {
                    bad = 1;
                    break;
                }
            }
            snprintf(label, sizeof(label),
                     "常量保持性：y=%g 的全部 %d 行输出仍为 %g", c, lines, c);
            expect(lines > 0 && !bad, label, bad ? "存在偏离常量的输出点" : "");
        }
    }

    /* ── 4. P1 输入点包含性（手册明示契约）── */
    {
        /* 数据集：y = x^2，x = 0,1,2,3,4 */
        static const double XS[] = { 0, 1, 2, 3, 4 };
        int j, hits = 0;
        fp = write_data("parabola.txt", "0 0\n1 1\n2 4\n3 9\n4 16\n");
        if (fp) {
            snprintf(args, sizeof(args), "\"%s\"", fp);
            rc = run_capture(args, buf, sizeof(buf));
            printf("── 输入点包含性 y=x^2（5 个输入点）\n");
            expect(rc == 0, "抛物线数据集退出码 (期望 0)", "");
            lines = count_lines(buf);
            for (j = 0; j < 5; j++) {
                int q, found = 0;
                for (q = 0; q < lines; q++) {
                    double x, y;
                    if (!get_point(buf, q, &x, &y))
                        continue;
                    if (fabs(x - XS[j]) < 1e-9 && fabs(y - XS[j] * XS[j]) < 1e-6) {
                        found = 1;
                        break;
                    }
                }
                if (found)
                    hits++;
                else {
                    snprintf(label, sizeof(label),
                             "输入点 (%g, %g) 出现在输出中", XS[j], XS[j] * XS[j]);
                    expect(0, label, "未找到");
                }
            }
            snprintf(label, sizeof(label),
                     "全部 5 个输入点都出现在输出中（实际命中 %d 个）", hits);
            expect(hits == 5, label, hits == 5 ? "" : "有缺失");
        }
    }

    /* ── 5. 结构属性：x 严格递增 + 行数不少于输入点数 + 首末 x 等于输入范围 ── */
    fp = write_data("range.txt", "0 0\n1 1\n2 4\n3 9\n4 16\n");
    if (fp) {
        double px = -1e300, lx = 0, ly = 0, fx = 0, fy = 0;
        int bad = 0;
        snprintf(args, sizeof(args), "\"%s\"", fp);
        rc = run_capture(args, buf, sizeof(buf));
        lines = count_lines(buf);
        printf("── 结构属性（默认输出 %d 行）\n", lines);
        for (i = 0; i < lines; i++) {
            double x, y;
            if (!get_point(buf, i, &x, &y)) {
                bad = 1;
                break;
            }
            if (i == 0) {
                fx = x; fy = y;
            }
            if (x <= px) {
                bad = 1;
                break;
            }
            px = x; lx = x; ly = y;
        }
        expect(!bad, "输出 x 严格递增", bad ? "存在非递增或不可解析的行" : "");
        expect(lines >= 5, "输出行数不少于输入点数 (5)", "");
        expect(fabs(fx - 0.0) < 1e-9, "首点 x == 输入最小 x (0)", "");
        expect(fabs(lx - 4.0) < 1e-9, "末点 x == 输入最大 x (4)", "");
        expect(fabs(fy - 0.0) < 1e-9 && fabs(ly - 16.0) < 1e-6,
               "首末 y 与输入端点一致 (0 / 16)", "");
    }

    /* ── 6. -n 属性：各档均成功、行数不少于输入点数、且落在 [输入点数, 2n+2] 内 ──
     *   ★ 实测行数 **不随 n 单调**（-n 3→7 行、-n 4→5 行）：因为输出必须包含
     *     原始输入点（手册契约），当 n 要求的区间数少于输入点数时无法再压缩，
     *     行数被输入点数托底。故不硬编码每档行数、也不断言单调性，改用两条
     *     真实成立的属性；另对 n 远大于输入点数的稳定区间断言精确值。 */
    {
        static const int NS[] = { 2, 3, 4, 5, 10, 20 };
        int k, ge = 1, ranged = 1;
        printf("── -n 输出行数属性\n");
        for (k = 0; k < 6; k++) {
            snprintf(args, sizeof(args), "-n %d \"%s\"", NS[k], fp);
            rc = run_capture(args, buf, sizeof(buf));
            lines = count_lines(buf);
            printf("     -n %-3d → %d 行\n", NS[k], lines);
            if (lines < 5)
                ge = 0;
            if (lines > 2 * NS[k] + 2)
                ranged = 0;
            snprintf(label, sizeof(label), "-n %d 退出码 (期望 0)", NS[k]);
            expect(rc == 0, label, "");
        }
        expect(ge, "-n 各档输出行数均不少于输入点数 (5)", "");
        expect(ranged, "-n 各档输出行数不超过 2n+2（手册：approx. n intervals）", "");
    }
    /* n 远大于输入点数时进入稳定区间：行数 == n+1 */
    snprintf(args, sizeof(args), "-n 20 \"%s\"", fp);
    rc = run_capture(args, buf, sizeof(buf));
    lines = count_lines(buf);
    expect(lines == 21, "-n 20 时输出 21 行（20 个区间）", "");

    /* ── 7. 默认等间距（默认 100 个区间）── */
    printf("── 默认输出行数\n");
    snprintf(args, sizeof(args), "\"%s\"", fp);
    rc = run_capture(args, buf, sizeof(buf));
    lines = count_lines(buf);
    snprintf(label, sizeof(label), "默认输出 101 行（100 个区间），实际 %d", lines);
    expect(lines == 101, label, "");
    {
        double x1, y1, x2, y2;
        if (get_point(buf, 0, &x0, &y0) && get_point(buf, 1, &x1, &y1)
            && get_point(buf, 2, &x2, &y2)) {
            double d1 = x1 - x0, d2 = x2 - x1;
            expect(fabs(d1 - d2) < 1e-9 && fabs(d1 - 0.04) < 1e-9,
                   "前三点等间距 0.04（4/100）", "");
        }
    }

    /* ── 8. -a 自动 abscissa：输入只有 y ── */
    {
        const char *ay;
        printf("── -a 1（输入仅 y，x 自动）\n");
        ay = write_data("ysonly.txt", "1\n3\n5\n7\n");
        if (ay) {
            snprintf(args, sizeof(args), "-a 1 \"%s\"", ay);
            rc = run_capture(args, buf, sizeof(buf));
            expect(rc == 0, "-a 1 退出码 (期望 0)", "");
            if (get_point(buf, 0, &x0, &y0)) {
                expect(fabs(x0 - 0.0) < 1e-9 && fabs(y0 - 1.0) < 1e-9,
                       "-a 1 输出首点 x=0（自动 abscissa 从 0 起）", "");
            } else {
                expect(0, "-a 1 输出首点 x=0", buf);
            }
            expect(count_lines(buf) > 1, "-a 1 产出插值点（行数 > 1）", "");
        }
        printf("── -a 缺少参数（无输入文件，读 stdin）\n");
        /* 注意：不能写成 "-a <file>"——那样文件会被当成 xstep 参数；
         * 这里刻意只给 -a 且不给任何文件，让该选项真正缺参。
         * ★ 实测：上游打印错误与用法后**退出码仍为 0**（非 0 退出并非其契约），
         *   故断言"报错信息 + 用法块 + 未崩溃"，不把退出码写成期望值。 */
        rc = run_capture("-a", buf, sizeof(buf));
        printf("     [INFO] -a 缺参时实测退出码 = %d\n", rc);
        expect(rc >= 0, "-a 缺参未导致进程异常终止", "");
        expect_contains("-a 缺参", buf, "option requires an argument");
        expect_contains("-a 缺参打印用法", buf, "[-hv][-a [xstep]]");
    }

    /* ── 9. 输入乱序时输出仍递增 ── */
    printf("── 输入 x 递减（3 2 1）\n");
    fp = write_data("desc.txt", "3 9\n2 4\n1 1\n");
    if (fp) {
        snprintf(args, sizeof(args), "\"%s\"", fp);
        rc = run_capture(args, buf, sizeof(buf));
        expect(rc == 0, "递减输入退出码 (期望 0)", "");
        if (get_point(buf, 0, &x0, &y0))
            expect(fabs(x0 - 1.0) < 1e-9, "递减输入被升序整理（首点 x=1）", "");
        else
            expect(0, "递减输入被升序整理", buf);
    }

    /* ── 10. 错误路径 ── */
    printf("── 非数字输入\n");
    fp = write_data("garbage.txt", "a b\n");
    if (fp) {
        snprintf(args, sizeof(args), "\"%s\"", fp);
        rc = run_capture(args, buf, sizeof(buf));
        expect_contains("非数字", buf, "parse error");
    }

    printf("── 打开不存在的文件\n");
    snprintf(args, sizeof(args), "\"%s/definitely-missing.dat\"", g_scratch);
    rc = run_capture(args, buf, sizeof(buf));
    expect_contains("不存在文件", buf, "can't open");

summary:
    printf("\n=== 汇总: %d 通过, %d 失败 ===\n", g_pass, g_fail);
    return g_fail == 0 ? 0 : 1;
}
