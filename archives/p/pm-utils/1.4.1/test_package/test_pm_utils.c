/* test_pm_utils.c — pm-utils 1.4.1 消费者测试
 *
 * 两个产物都是可执行程序、没有可链接的库 API，所以用例按「该程序的真实
 * 调用方式」验证：把包内 bin/ 下的 pm-pmu / pm-reset-swap 以子进程拉起。
 *
 * ★ 这两个工具的工作目标路径 /sys/devices/system/cpu/intel_pstate/ 是
 *   Intel P-state 专用节点，OHOS PC 上并不存在。所以「读不到」这条优雅降级
 *   路径不是缺陷而是**真实行为**，本组用例正是把它钉死。
 * ★ pm-reset-swap 的退出码分三档，是本组最值得断言的地方：
 *     参数是有效可读普通文件（/dev/zero，读出来全零，恰好像合法 swap 签名）
 *       → RC=0
 *     参数打不开（不存在路径，或把 -h/--check 之类误当设备节点）
 *       → RC=1
 *     参数能打开但取 swap 签名失败（/dev/null 读不出内容）
 *       → RC=2
 * ★ 全部期望文本与期望退出码取自 qemu-aarch64 + OHOS sysroot 下的**实测输出**。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
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

static char *slurp(const char *path)
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
    return buf;
}

/* 跑一次程序。stdout+stderr 并到 out_path，返回退出码。 */
static int run_tool(const char *exe, const char *run_dir, const char *args,
                    const char *out_path)
{
    pid_t pid;
    int status = -1;
    char script[2048];
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
    char p_pmu[1300], p_swap[1300];
    char *text = NULL;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: test_pm_utils <package_root>\n");
        return 2;
    }
    if (!realpath(argv[1], pkg)) {
        fprintf(stderr, "FATAL: package root not found: %s\n", argv[1]);
        return 2;
    }
    snprintf(p_pmu, sizeof(p_pmu), "%s/bin/pm-pmu", pkg);
    snprintf(p_swap, sizeof(p_swap), "%s/bin/pm-reset-swap", pkg);
    if (access(p_pmu, X_OK) != 0 || access(p_swap, X_OK) != 0) {
        fprintf(stderr, "FATAL: pm-utils binaries missing under %s/bin\n", pkg);
        return 2;
    }

    snprintf(run_dir, sizeof(run_dir), "pmutils_run");
    mkdir(run_dir, 0755);
    snprintf(out_path, sizeof(out_path), "%s/run.out", run_dir);

    /* ---- A：pm-pmu 的参数解析 ---- */
    printf("== A: pm-pmu argument handling ==\n");
    rc = run_tool(p_pmu, run_dir, NULL, out_path);
    okf(rc == 1, "A1 pm-pmu with no args exits 1", rc, 1);
    text = slurp(out_path);
    ok(text && strstr(text, "usage: pm-pmu --suspend | --check") != NULL,
       "A2 pm-pmu prints its one-line usage");
    free(text);

    rc = run_tool(p_pmu, run_dir, "--help", out_path);
    okf(rc == 0, "A3 pm-pmu --help exits 0 (the only arg that succeeds on OHOS)", rc, 0);
    text = slurp(out_path);
    ok(text && strstr(text, "--suspend | --check") != NULL,
       "A4 --help still prints the usage line");
    free(text);

    rc = run_tool(p_pmu, run_dir, "-h", out_path);
    okf(rc == 1, "A5 pm-pmu -h is NOT accepted (only --help is)", rc, 1);
    free(slurp(out_path));

    rc = run_tool(p_pmu, run_dir, "-Z", out_path);
    okf(rc == 1, "A6 an unknown option exits 1", rc, 1);
    free(slurp(out_path));

    /* ---- B：pm-pmu 的工作路径在 OHOS 上不存在 → 静默失败 ---- */
    printf("== B: pm-pmu degrades when intel_pstate is absent ==\n");
    rc = run_tool(p_pmu, run_dir, "--suspend", out_path);
    okf(rc == 1, "B1 --suspend exits 1 without printing usage", rc, 1);
    text = slurp(out_path);
    ok(text && strstr(text, "usage:") == NULL,
       "B2 --suspend prints no usage line (it failed, not mis-parsed)");
    free(text);

    rc = run_tool(p_pmu, run_dir, "--check", out_path);
    okf(rc == 1, "B3 --check exits 1 as well", rc, 1);
    free(slurp(out_path));

    /* 幂等：连跑两次 --check 退出码必须一致（共享真机 worker 上不 flaky） */
    {
        int r1 = run_tool(p_pmu, run_dir, "--check", out_path);
        int r2 = run_tool(p_pmu, run_dir, "--check", out_path);
        free(slurp(out_path));
        okf(r1 == r2, "B4 --check is repeatable (same rc twice)", r1, r2);
    }

    /* ---- C：pm-reset-swap 的三档退出码 ---- */
    printf("== C: pm-reset-swap exit-code ladder ==\n");
    rc = run_tool(p_swap, run_dir, NULL, out_path);
    okf(rc == 1, "C1 with no argument exits 1", rc, 1);
    text = slurp(out_path);
    ok(text && strstr(text, "usage: pm-reset-swap <device node>") != NULL,
       "C2 prints the one-line usage");
    free(text);

    rc = run_tool(p_swap, run_dir, "--help", out_path);
    okf(rc == 0, "C3 --help exits 0", rc, 0);
    free(slurp(out_path));

    /* -h 不会被当成「帮助」：pm-reset-swap 把参数一律当设备节点 */
    rc = run_tool(p_swap, run_dir, "-h", out_path);
    okf(rc == 1, "C4 -h is treated as a device node, not help, and exits 1", rc, 1);
    text = slurp(out_path);
    ok(text && strstr(text, "Could not open \"-h\"") != NULL,
       "C5 the diagnostic quotes the bogus node name");
    ok(text && strstr(text, "No such file or directory") != NULL,
       "C6 the diagnostic carries the errno text");
    free(text);

    rc = run_tool(p_swap, run_dir, "/nonexistent", out_path);
    okf(rc == 1, "C7 a missing path exits 1", rc, 1);
    text = slurp(out_path);
    ok(text && strstr(text, "Could not open \"/nonexistent\"") != NULL,
       "C8 names the missing path");
    free(text);

    /* /dev/null：能打开，但取 swap 签名失败 → 第三档退出码 2 */
    rc = run_tool(p_swap, run_dir, "/dev/null", out_path);
    okf(rc == 2, "C9 an openable node whose signature cannot be read exits 2", rc, 2);
    text = slurp(out_path);
    ok(text && strstr(text, "for swap signature") != NULL,
       "C10 the diagnostic says the signature check failed");
    ok(text && strstr(text, "/dev/null") != NULL,
       "C11 the diagnostic names the node");
    free(text);

    /* /dev/zero：读出来全是零，恰好匹配合法 swap 签名 → 成功 */
    rc = run_tool(p_swap, run_dir, "/dev/zero", out_path);
    okf(rc == 0, "C12 an all-zero node looks like a valid signature and exits 0", rc, 0);

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
