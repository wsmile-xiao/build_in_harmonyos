/* test_lpctools.c — lpctools 1.07 消费者测试
 *
 * lpctools 的三个产物都是可执行程序、没有可链接的库 API，所以用例按
 * 「该程序的真实调用方式」验证：把包内 bin/ 下的三个二进制以子进程拉起，
 * 对其用法输出、选项解析诊断、退出码做确定性断言。
 *
 * ★ 所有期望文本与期望退出码均逐字取自 qemu-aarch64 + OHOS sysroot 下的
 *   **实测输出**，不是照抄源码里的字符串表。
 * ★ 全部用例零硬件：`-d /dev/null` 让串口握手立刻 EOF，因此
 *   "读不到器件" 这条真实失败路径也能稳定复现，不需要接 LPC 板子。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>

static int failures = 0;
static int checks = 0;

static void ok(int cond, const char *what)
{
    checks++;
    printf("  [%s] %s\n", cond ? "PASS" : "FAIL", what);
    if (!cond) failures++;
}

static void okf(int cond, const char *what, long got, long want)
{
    checks++;
    printf("  [%s] %s  (got=%ld want=%ld)\n", cond ? "PASS" : "FAIL", what, got, want);
    if (!cond) failures++;
}

static char *slurp(const char *path, long *len)
{
    FILE *f = fopen(path, "rb");
    long n;
    char *buf;
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    n = ftell(f);
    fseek(f, 0, SEEK_SET);
    buf = (char *)malloc((size_t)n + 1);
    if (!buf) { fclose(f); return NULL; }
    n = (long)fread(buf, 1, (size_t)n, f);
    buf[n] = '\0';
    fclose(f);
    if (len) *len = n;
    return buf;
}

/* 跑一次程序。stdout+stderr 并到 out_path，返回退出码。
 * 子进程 chdir 到 run_dir，所以重定向必须用裸文件名。 */
static int run_tool(const char *exe, const char *run_dir, const char *args,
                    const char *out_path)
{
    pid_t pid;
    int status = -1;
    char script[4096];
    const char *ob = strrchr(out_path, '/');
    ob = ob ? ob + 1 : out_path;

    unlink(out_path);
    snprintf(script, sizeof(script), "exec \"%s\" %s >\"%s\" 2>&1;",
             exe, args ? args : "", ob);

    pid = fork();
    if (pid == 0) {
        if (chdir(run_dir) != 0) _exit(127);
        execl("/bin/sh", "sh", "-c", script, (char *)NULL);
        _exit(127);
    }
    if (pid < 0) return -1;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

int main(int argc, char **argv)
{
    char pkg[1024], run_dir[1200], out_path[1400];
    char p_prog[1300], p_isp[1300], p_check[1300];
    char *text = NULL;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: test_lpctools <package_root>\n");
        return 2;
    }
    if (!realpath(argv[1], pkg)) {
        fprintf(stderr, "FATAL: package root not found: %s\n", argv[1]);
        return 2;
    }
    snprintf(p_prog, sizeof(p_prog), "%s/bin/lpcprog", pkg);
    snprintf(p_isp, sizeof(p_isp), "%s/bin/lpcisp", pkg);
    snprintf(p_check, sizeof(p_check), "%s/bin/lpc_binary_check", pkg);
    if (access(p_prog, X_OK) != 0 || access(p_isp, X_OK) != 0 ||
        access(p_check, X_OK) != 0) {
        fprintf(stderr, "FATAL: lpctools binaries missing under %s/bin\n", pkg);
        return 2;
    }
    /* 芯片型号描述表：lpcprog/lpcisp 的 -p 默认值，包内那份 */
    {
        char pd[1400];
        struct stat st;
        snprintf(pd, sizeof(pd), "%s/share/lpctools/lpctools_parts.def", pkg);
        ok(stat(pd, &st) == 0 && st.st_size > 0,
           "A0 the packaged parts description table is present");
    }

    snprintf(run_dir, sizeof(run_dir), "lpctools_run");
    mkdir(run_dir, 0755);
    snprintf(out_path, sizeof(out_path), "%s/run.out", run_dir);

    /* lpcprog / lpcisp 的 -p 默认值是 /etc/lpctools_parts.def 或当前目录下的
     * lpctools_parts.def。测试在 lpctools_run 里跑，所以必须把包内那份复制
     * 进 cwd，否则走的是"找不到型号表"这条分支，诊断文本与真实器件路径不同。 */
    {
        char src_pd[1400], dst_pd[1400];
        long n = 0;
        char *buf;
        snprintf(src_pd, sizeof(src_pd), "%s/share/lpctools/lpctools_parts.def", pkg);
        snprintf(dst_pd, sizeof(dst_pd), "%s/lpctools_parts.def", run_dir);
        buf = slurp(src_pd, &n);
        if (buf) {
            FILE *f = fopen(dst_pd, "wb");
            if (f) { fwrite(buf, 1, (size_t)n, f); fclose(f); }
            free(buf);
        }
    }

    /* ---- A：lpcprog 的用法与选项解析 ---- */
    printf("== A: lpcprog usage and option parsing ==\n");
    rc = run_tool(p_prog, run_dir, NULL, out_path);
    okf(rc == 255, "A1 lpcprog with no args exits 255", rc, 255);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "No command given. use -h or --help for help on available commands.") != NULL,
       "A2 lpcprog asks for a command");
    free(text);

    rc = run_tool(p_prog, run_dir, "-h", out_path);
    okf(rc == 0, "A3 lpcprog -h exits 0 (unlike lpc_binary_check -h, which exits 255)", rc, 0);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "LPC ISP Prog tool") != NULL, "A4 help shows the tool banner");
    /* ★ 用法行里嵌的是 argv[0]，不是字面量 "./lpcprog"：实测得到的是
     *   Usage: /mnt/c/.../lpcbuild/lpcprog -d <dev_name> -c <command> ...
     *   即程序把自己被调用的完整路径原样打出来。所以断言只能查 argv[0]
     *   之后的那一段，查整行会随调用路径变化而失效。 */
    ok(text && strstr(text, "-d <dev_name> -c <command>") != NULL,
       "A5 help shows the usage line (argv[0]-independent part)");
    ok(text && strstr(text, "dump, flash, id, blank, go") != NULL,
       "A6 help lists all five commands");
    ok(text && strstr(text, "Default baudrate is B115200") != NULL,
       "A7 help states the default baudrate");
    free(text);

    rc = run_tool(p_prog, run_dir, "--help", out_path);
    okf(rc == 0, "A8 lpcprog --help also exits 0", rc, 0);
    free(slurp(out_path, NULL));

    rc = run_tool(p_prog, run_dir, "--bogus", out_path);
    okf(rc == 0, "A9 lpcprog --bogus exits 0 (getopt path prints usage then returns)", rc, 0);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "unrecognized option: bogus") != NULL,
       "A10 lpcprog names the offending option");
    ok(text && strstr(text, "LPC ISP Prog tool") != NULL,
       "A11 lpcprog also prints usage after an unknown option");
    free(text);

    /* ---- B：lpcprog 的两条失败路径（零硬件）---- */
    printf("== B: lpcprog failure paths without hardware ==\n");
    rc = run_tool(p_prog, run_dir, "-c id", out_path);
    okf(rc == 0, "B1 -c id without -d exits 0 (prints diagnostic + usage)", rc, 0);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "No serial device given, exiting") != NULL,
       "B2 reports the missing serial device");
    free(text);

    rc = run_tool(p_prog, run_dir, "-d /dev/null -c id", out_path);
    okf(rc == 255, "B3 talking to a non-device serial line exits 255", rc, 255);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "serial_read: end of file") != NULL,
       "B4 reports end-of-file on the serial link");
    ok(text && strstr(text, "Unable to connect to target") != NULL,
       "B5 reports it could not reach the target");
    free(text);

    /* ---- C：lpcisp ---- */
    printf("== C: lpcisp ==\n");
    rc = run_tool(p_isp, run_dir, NULL, out_path);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "No serial device given") != NULL,
       "C1 lpcisp without a device says so");
    okf(rc == 0, "C2 lpcisp without a device exits 0", rc, 0);
    free(text);

    rc = run_tool(p_isp, run_dir, "-h", out_path);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "[options] device [-s | --synchronize]") != NULL,
       "C3 lpcisp help shows its positional-device usage");
    ok(text && strstr(text, "read-part-id") != NULL,
       "C4 lpcisp help lists read-part-id");
    ok(text && strstr(text, "Default baudrate is B115200") != NULL,
       "C5 lpcisp help states the default baudrate");
    free(text);

    /* lpcisp 把 device 当位置参数，不认 -c —— 与 lpcprog 的 -c 语义不同 */
    rc = run_tool(p_isp, run_dir, "-c id", out_path);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "unrecognized option: c") != NULL &&
       strstr(text, "lpcisp") != NULL,
       "C6 lpcisp rejects -c (device is positional there, unlike lpcprog)");
    free(text);

    /* ---- D：lpc_binary_check ---- */
    printf("== D: lpc_binary_check ==\n");
    rc = run_tool(p_check, run_dir, NULL, out_path);
    okf(rc == 255, "D1 with no file name exits 255", rc, 255);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "Need one (and only one) file name to check.") != NULL,
       "D2 asks for exactly one file name");
    free(text);

    rc = run_tool(p_check, run_dir, "-h", out_path);
    okf(rc == 255, "D3 -h exits 255 — 与 lpcprog -h 的 0 不同，是真实的行为差异", rc, 255);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "LPC binary check") != NULL, "D4 help shows the tool banner");
    ok(text && strstr(text, "[options] [prog file name]") != NULL,
       "D5 help shows the usage line (argv[0]-independent part)");
    ok(text && strstr(text, "--no-user-code") != NULL,
       "D6 help documents --no-user-code");
    free(text);

    rc = run_tool(p_check, run_dir, "/dev/null", out_path);
    okf(rc == 254, "D7 checking an empty file exits 254", rc, 254);

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
