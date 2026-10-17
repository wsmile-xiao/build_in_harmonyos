/*
 * sntop 1.4.3 消费者测试（test_package/src/test_sntop.c）
 *
 * 以"使用者身份"驱动被测包真正交付的那个产物 —— bin/sntop —— 并把它
 * 对外承诺的行为逐条断言成退出码，不做只 include / 只链接 / 只打印式的
 * 空壳检查。
 *
 * 覆盖三条相互独立的行为面：
 *   1) 版本面：--version 必须原样打印上游版本串 sntop v1.4.3。不用子串
 *      "sntop" 断言 —— 二进制名本身含该串，找不到二进制时 shell 的报错
 *      里也会含它，会造成假阳性。
 *   2) 用法面：--help 走 getopt_long 的 'h' 分支，打印 Usage 与整张选项表。
 *   3) 核心功能面：守护 + 单次 + HTML（-d -o -w -p）这条路径全程不碰
 *      curses（源码里所有 curses 调用都被 !(flags & DAEMON) 包住），
 *      因此能在无 tty 的 CI 里真跑一遍完整链路：解析配置文件 → 经
 *      /bin/sh 执行与 -p 拼出的完全相同的 ping 命令行 → 判定 UP/DOWN
 *      → 渲染 HTML 报表。
 *      断言方式是"在同一台机器上用同一条 ping 命令独立取地面真值，
 *      再要求被测程序报告的每个主机状态与之一致"，而不是写死某台主机
 *      必然 UP 或必然 DOWN —— 后者在受限网络环境里会变成假失败。
 *
 * 用法： test_sntop <sntop 二进制绝对路径> <工作目录绝对路径>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>

#define UP_COLOR   "#00BB00"
#define DOWN_COLOR "#CC0000"

static int checks_total;
static int checks_failed;

#define CHECK(cond, what)                                                   \
    do {                                                                    \
        checks_total++;                                                     \
        if (cond) {                                                         \
            printf("PASS[%02d]: %s\n", checks_total, (what));               \
        } else {                                                            \
            checks_failed++;                                                \
            printf("FAIL[%02d]: %s\n", checks_total, (what));               \
        }                                                                   \
    } while (0)

/* 执行命令并捕获 stdout+stderr；返回退出码，popen 自身失败返回 -1。 */
static int run_capture(const char *cmd, char *out, size_t outsz)
{
    FILE *fp;
    size_t used = 0;

    if (out && outsz) {
        out[0] = '\0';
    }
    fp = popen(cmd, "r");
    if (!fp) {
        fprintf(stderr, "popen failed for: %s (%s)\n", cmd, strerror(errno));
        return -1;
    }
    if (out && outsz > 1) {
        char buf[512];
        size_t n;
        while ((n = fread(buf, 1, sizeof(buf), fp)) > 0) {
            size_t room = outsz - 1 - used;
            size_t take = n < room ? n : room;
            if (take) {
                memcpy(out + used, buf, take);
                used += take;
                out[used] = '\0';
            }
            if (take < n) {
                break;              /* 缓冲满：保留前缀用于诊断 */
            }
        }
    }
    return WEXITSTATUS(pclose(fp));
}

/* 取某台主机的地面真值：命令行与 sntop -p 拼出的完全一致
 * （sntop.h: PING_LINE "ping -c 1 -s 8 -q" + host + PING_END）。
 * 返回 1=UP，0=DOWN，-1=本机没有可用的 ping(1)，该组断言不可判定。 */
static int ping_truth(const char *host)
{
    char cmd[512];
    int rc;

    snprintf(cmd, sizeof(cmd),
             "ping -c 1 -s 8 -q %s 2> /dev/null > /dev/null", host);
    rc = system(cmd);
    if (rc == -1) {
        return -1;
    }
    if (WIFEXITED(rc) && WEXITSTATUS(rc) == 127) {
        return -1;
    }
    return (WIFEXITED(rc) && WEXITSTATUS(rc) == 0) ? 1 : 0;
}

static int file_exists(const char *p)
{
    struct stat st;
    return stat(p, &st) == 0;
}

/* 在报表里定位某主机那一行的状态色。
 * 行的形状： <TD BGCOLOR=#EEEEEE>NAME</TD> ... <TD ...COLOR...> ...
 * 搜索窗口止于下一个 <TR>，避免读到别的主机的颜色。
 * 返回 1=UP，0=DOWN，-1=未找到该主机行或行内没有状态色。 */
static int html_status(const char *html, const char *name)
{
    char needle[256];
    const char *row;
    const char *p;
    const char *end;

    snprintf(needle, sizeof(needle), "<TD BGCOLOR=#EEEEEE>%s</TD>", name);
    row = strstr(html, needle);
    if (!row) {
        return -1;
    }
    p = row + strlen(needle);
    end = strstr(p, "<TR>");
    if (!end) {
        end = strstr(p, "</TABLE>");
    }
    if (!end) {
        end = p + strlen(p);
    }
    while (p < end) {
        if (!strncmp(p, UP_COLOR, strlen(UP_COLOR))) {
            return 1;
        }
        if (!strncmp(p, DOWN_COLOR, strlen(DOWN_COLOR))) {
            return 0;
        }
        p++;
    }
    return -1;
}

/* 解析统计行 "<P><B>N</B> hosts polled: <B>U</B> up, <B>D</B> down"。
 * 成功返回 0 并填三个计数；找不到该行返回 -1。 */
static int html_counts(const char *html, int *total, int *up, int *down)
{
    const char *lp;
    const char *q;

    lp = strstr(html, " hosts polled: ");
    if (!lp) {
        return -1;
    }
    /* 回溯到本行的 <P><B> 开头；前文另有 <P><B>sntop network status
     * ... 的标题段，必须按"离统计行最近的那一个"来定位。 */
    for (q = lp; q > html; q--) {
        if (!strncmp(q, "<P><B>", 6)) {
            break;
        }
    }
    if (q == html) {
        return -1;
    }
    if (sscanf(q, "<P><B>%d</B> hosts polled: <B>%d</B> up, <B>%d</B> down",
               total, up, down) != 3) {
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *bin;
    const char *work;
    char conf[512];
    char html[512];
    char cmd[2048];
    char out[8192];
    char *text;
    long sz;
    FILE *fp;
    int rc;
    int total = 0, up = 0, down = 0;
    int t1, t2, s1, s2;
    int counts_ok;

    if (argc < 3) {
        fprintf(stderr, "usage: %s <sntop-binary> <work-dir>\n", argv[0]);
        return 2;
    }
    bin = argv[1];
    work = argv[2];

    CHECK(file_exists(bin), "被测包产物 bin/sntop 存在");
    if (!file_exists(bin)) {
        fprintf(stderr, "被测二进制缺失，后续断言无法执行\n");
        return 1;
    }

    /* ---- 行为面 1：版本 ---- */
    snprintf(cmd, sizeof(cmd), "\"%s\" --version 2>&1", bin);
    rc = run_capture(cmd, out, sizeof(out));
    CHECK(rc == 0, "--version 退出码为 0");
    CHECK(strstr(out, "sntop v1.4.3") != NULL,
          "--version 输出含上游版本串 sntop v1.4.3");

    /* ---- 行为面 2：用法 ---- */
    snprintf(cmd, sizeof(cmd), "\"%s\" --help 2>&1", bin);
    rc = run_capture(cmd, out, sizeof(out));
    CHECK(rc == 0, "--help 退出码为 0");
    CHECK(strstr(out, "Usage:") != NULL, "--help 输出含 Usage 用法行");
    CHECK(strstr(out, "-r, --refresh") != NULL,
          "--help 输出含 refresh 选项（说明整张选项表来自被测程序）");

    /* ---- 行为面 3：守护 + 单次 + HTML，真跑轮询判定链路 ---- */
    snprintf(conf, sizeof(conf), "%s/sntoprc", work);
    snprintf(html, sizeof(html), "%s/status.html", work);
    fp = fopen(conf, "w");
    if (!fp) {
        fprintf(stderr, "cannot write test conf %s: %s\n", conf,
                strerror(errno));
        return 1;
    }
    fputs("firsthost\n127.0.0.1\ntest loopback\n", fp);
    fputs("secondhost\n192.0.2.1\ntest reserved\n", fp);
    fclose(fp);
    unlink(html);

    snprintf(cmd, sizeof(cmd),
             "TERM=dumb \"%s\" -d -o -w -p -f \"%s\" -e \"%s\" 2>&1",
             bin, conf, html);
    rc = run_capture(cmd, out, sizeof(out));
    CHECK(rc == 0, "守护模式轮询一轮并产出报表，退出码为 0");
    if (rc != 0) {
        fprintf(stderr, "被测程序输出：%s\n", out);
    }
    CHECK(file_exists(html), "HTML 报表文件已生成");
    if (!file_exists(html)) {
        printf(" checks=%d failed=%d\n", checks_total, checks_failed);
        return 1;
    }

    fp = fopen(html, "rb");
    if (!fp) {
        fprintf(stderr, "cannot open %s: %s\n", html, strerror(errno));
        return 1;
    }
    fseek(fp, 0, SEEK_END);
    sz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    if (sz < 1 || sz > 200000) {
        fclose(fp);
        fprintf(stderr, "unexpected report size %ld\n", sz);
        return 1;
    }
    text = calloc(1, (size_t)sz + 1);
    if (!text) {
        fclose(fp);
        return 1;
    }
    if (fread(text, 1, (size_t)sz, fp) == 0) {
        text[0] = '\0';
    }
    fclose(fp);

    CHECK(strstr(text, "<TD BGCOLOR=#EEEEEE>firsthost</TD>") != NULL,
          "报表含第一台主机的行");
    CHECK(strstr(text, "<TD BGCOLOR=#EEEEEE>secondhost</TD>") != NULL,
          "报表含第二台主机的行");
    CHECK(strstr(text, "Generated by") != NULL,
          "报表由被测程序自身署名生成（排除读到残留旧文件的可能）");

    t1 = ping_truth("127.0.0.1");
    t2 = ping_truth("192.0.2.1");
    s1 = html_status(text, "firsthost");
    s2 = html_status(text, "secondhost");

    if (t1 == -1 || t2 == -1) {
        printf("SKIP: 本机没有可用的 ping(1)，状态一致性断言不可判定，已跳过\n");
        CHECK(s1 == 1 || s1 == 0, "firsthost 行内给出了明确状态色");
        CHECK(s2 == 1 || s2 == 0, "secondhost 行内给出了明确状态色");
    } else {
        CHECK(s1 == t1, "firsthost 报告状态与同机同命令 ping 的地面真值一致");
        CHECK(s2 == t2, "secondhost 报告状态与同机同命令 ping 的地面真值一致");
    }

    counts_ok = (html_counts(text, &total, &up, &down) == 0);
    CHECK(counts_ok, "报表含可解析的 hosts polled 统计行");
    if (counts_ok) {
        CHECK(total == 2, "统计行主机数等于配置清单条目数 2");
        CHECK(up + down == total, "统计行 up 与 down 之和等于总数");
        if (t1 != -1 && t2 != -1) {
            CHECK(up == ((t1 == 1) + (t2 == 1)),
                  "统计行 up 计数与地面真值一致");
        }
    }

    free(text);
    printf(" checks=%d failed=%d\n", checks_total, checks_failed);
    return checks_failed ? 1 : 0;
}
