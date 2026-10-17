/* itools 1.1 消费者测试（路径 A 赛道二：真实编译 + 真实运行 + 断言决定退出码）
 *
 * 设计口径：
 *  - 三个被测对象都是命令行程序，所以"消费者"以调用者身份 spawn 它们并断言
 *    退出码与输出结构，而不是只 include 头文件。
 *  - 退出码断点直接取自上游源码：usage(leave) 里 ical/idate exit(20)、
 *    ipraytime exit(10)（见 ical.c / idate.c / ipraytime.c 各自的 usage()）。
 *  - 最强的一条是 T5 的 G2H/H2G 往返闭合：它证明链接到的 libitl 真在算，
 *    而不是"打印了点什么"。
 *  - 输出解析锚点取自 idate.c 的字面量 "+ Input    : %2d/%2d/%4d" 与
 *    "+ Output   : %2d/%2d/%4d"（%2d 会把个位数打成空格，故用 %d 解析容忍）。
 *  - 编译成 ELF 而不是写 shell 脚本：CI worker 拒跑 shebang 脚本
 *    （checklist #8，与 `Can't exec "aclocal"` 同源问题）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

#ifndef ITOOLS_BIN
#error "ITOOLS_BIN must be defined by the build"
#endif

/* ITOOLS_BIN 由 CMakeLists 以 "..." 形态传入，本身已是字符串字面量。 */
static int failures;
static int checks;

static void ok(int pass, const char *what)
{
    checks++;
    if (pass) {
        printf("PASS  %s\n", what);
    } else {
        failures++;
        printf("FAIL  %s\n", what);
    }
}

/* 运行 "<bindir>/<prog> <args>"，返回退出码；out 收 stdout+stderr（截断到 cap-1）。 */
static int run_tool(const char *prog, const char *args, char *out, size_t cap)
{
    char cmd[1024];
    FILE *pipe;
    size_t used = 0;
    int status;

    out[0] = '\0';
    snprintf(cmd, sizeof(cmd), "%s/%s %s </dev/null 2>&1", ITOOLS_BIN, prog, args);
    pipe = popen(cmd, "r");
    if (pipe == NULL)
        return -1;
    while (used + 1 < cap && fgets(out + used, (int)(cap - used), pipe) != NULL)
        used += strlen(out + used);
    out[cap - 1] = '\0';
    status = pclose(pipe);
    return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

static int has_digit(const char *s)
{
    while (*s) {
        if (*s >= '0' && *s <= '9')
            return 1;
        s++;
    }
    return 0;
}

/* 从 idate 输出里解析 "+ Output" 之后的第一个 dd/mm/yyyy。 */
static int output_date(const char *s, int *d, int *m, int *y)
{
    const char *at = strstr(s, "+ Output");
    if (at == NULL)
        return 0;
    return sscanf(at, " %*[^0-9]%d/%d/%d", d, m, y) == 3;
}

int main(void)
{
    char buf[8192];
    char arg[32];
    int rc;
    int hd, hm, hy;
    int gd, gm, gy;

    /* T1 ical: 回历月历表（锚点取真机实测输出 "Rabi II 1448 (A.H)" 里的纪元标记） */
    rc = run_tool("ical", "--gregorian 20260924", buf, sizeof(buf));
    ok(rc == 0, "ical --gregorian 20260924 退出码 0");
    ok(strstr(buf, "(A.H)") != NULL && has_digit(buf),
       "ical 输出含回历纪元标记 (A.H) 与日期数字（月历表已渲染，不是空跑）");

    /* T2 idate: 公历 -> 回历 */
    rc = run_tool("idate", "--gregorian 20260924", buf, sizeof(buf));
    ok(rc == 0, "idate --gregorian 20260924 退出码 0");
    ok(output_date(buf, &hd, &hm, &hy) && hy >= 1300 && hy <= 1600 &&
       hm >= 1 && hm <= 12 && hd >= 1 && hd <= 31,
       "idate 输出的回历日期落在合理区间（13xx-16xx 年 / 1-12 月 / 1-31 日）");

    /* T3 ipraytime: 祈祷时刻 + Qibla */
    rc = run_tool("ipraytime",
                  "--date 20260924 --latitude 24.4667 --longitude 54.3667 --utcdiff 4",
                  buf, sizeof(buf));
    ok(rc == 0, "ipraytime 参数化调用退出码 0");
    ok(strchr(buf, ':') != NULL && has_digit(buf),
       "ipraytime 输出含 hh:mm 时刻（真的算了而不是空跑）");

    /* T4 --help 的固定退出码：三个程序各不相同，是上游源码写死的 */
    ok(run_tool("ical", "--help", buf, sizeof(buf)) == 20,
       "ical --help 退出码 20（usage(1)->exit(20)）");
    ok(run_tool("idate", "--help", buf, sizeof(buf)) == 20,
       "idate --help 退出码 20（usage(1)->exit(20)）");
    ok(run_tool("ipraytime", "--help", buf, sizeof(buf)) == 10,
       "ipraytime --help 退出码 10（usage(1)->exit(10)）");

    /* T5 往返闭合：公历 -> 回历 -> 公历，且回到同一天的同一表示 */
    snprintf(arg, sizeof(arg), "--hijri %04d%02d%02d", hy, hm, hd);
    rc = run_tool("idate", arg, buf, sizeof(buf));
    ok(rc == 0, "idate 用 T2 得到的回历日期反算，退出码 0");
    ok(output_date(buf, &gd, &gm, &gy) && gd == 24 && gm == 9 && gy == 2026,
       "回历反算回公历 == 24/9/2026（G2H/H2G 往返闭合，证明 libitl 真被链上并算对）");

    /* T6 负路径：互斥参数必须干净报错，不能靠崩溃交差 */
    rc = run_tool("ical", "--gregorian --hijri 20260924", buf, sizeof(buf));
    ok(rc != 0 && rc != -1 && rc != 20,
       "ical 同时给 --gregorian 与 --hijri 时干净非零退出（信号死亡记 -1，判 FAIL）");

    printf("\nitools smoke: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
