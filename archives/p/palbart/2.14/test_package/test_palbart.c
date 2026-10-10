/* test_palbart.c — palbart 2.14 消费者测试
 *
 * palbart 是 GNU barcode 的 PostScript 驱动，性质与 mailto 的 CGI 类似：
 * 没有可链接的库 API，只有一个可执行文件。所以用例按「该程序的真实调用
 * 方式」验证——把包内 bin/palbart 以子进程拉起，喂入条码描述语言文件，
 * 对它产出的符号清单(.lst)、条码位流(.bin) 与诊断输出做确定性断言。
 *
 * ★ 全部 17 条断言的期望文本，均逐字取自 qemu-aarch64 + OHOS sysroot 下
 *   的**实测输出**（见 notes.md 的取证表），不是照抄源码里的注释或字符串表。
 * ★ 五组用例全部零网络、零设备依赖、零渲染器依赖：palbart 只做解释与编码，
 *   不调用 gnuplot / ghostscript，产物是纯文本清单与固定长度的位流。
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
    if (cond) {
        printf("  [PASS] %s\n", what);
    } else {
        printf("  [FAIL] %s\n", what);
        failures++;
    }
}

static void okf(int cond, const char *fmt, long got, long want)
{
    char buf[256];
    checks++;
    if (cond) {
        printf("  [PASS] ");
    } else {
        printf("  [FAIL] ");
        failures++;
    }
    printf(fmt, got, want);
    printf("  (got=%ld want=%ld)\n", got, want);
}

/* 把文件整体读进 malloc 缓冲；不存在时返回 NULL。 */
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

static int file_size(const char *path)
{
    struct stat st;
    if (stat(path, &st) != 0) return -1;
    return (int)st.st_size;
}

/* 在 run_dir 下跑一次 palbart：写输入文件 → fork/exec → 收集退出码、
 * stdout 文本、.lst 文本与 .bin 字节数。 */
static int run_palbart(const char *exe, const char *run_dir,
                       const char *input, int has_input,
                       char *out_text, size_t out_cap,
                       char *lst_text, size_t lst_cap,
                       int *bin_size)
{
    char in_path[1024], out_path[1024], lst_path[1024], bin_path[1024];
    pid_t pid;
    int status = -1, fd;
    char *got;

    /* palbart 把输入的扩展名替换成 .lst / .bin：bc.txt -> bc.lst + bc.bin
     * （实测：输入 bc.txt，产物 bc.lst 212B / bc.bin 256B）。 */
    snprintf(in_path, sizeof(in_path), "%s/bc.txt", run_dir);
    snprintf(out_path, sizeof(out_path), "%s/bc.out", run_dir);
    snprintf(lst_path, sizeof(lst_path), "%s/bc.lst", run_dir);
    snprintf(bin_path, sizeof(bin_path), "%s/bc.bin", run_dir);
    unlink(in_path); unlink(out_path); unlink(lst_path); unlink(bin_path);

    if (has_input) {
        FILE *f = fopen(in_path, "wb");
        if (!f) return -1;
        fputs(input, f);
        fclose(f);
    }

    pid = fork();
    if (pid == 0) {
        /* 子进程：切到 run_dir，stdout 重定向到 bc.out，再 exec palbart。 */
        if (chdir(run_dir) != 0) _exit(127);
        fd = open("bc.out", O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd < 0) _exit(127);
        dup2(fd, STDOUT_FILENO);
        dup2(fd, STDERR_FILENO);
        close(fd);
        if (has_input) execl(exe, "palbart", "bc.txt", (char *)NULL);
        else          execl(exe, "palbart", (char *)NULL);
        _exit(127);
    }
    if (pid < 0) return -1;
    waitpid(pid, &status, 0);

    out_text[0] = lst_text[0] = '\0';
    got = slurp(out_path, NULL);
    if (got) { strncpy(out_text, got, out_cap - 1); out_text[out_cap - 1] = '\0'; free(got); }
    got = slurp(lst_path, NULL);
    if (got) { strncpy(lst_text, got, lst_cap - 1); lst_text[lst_cap - 1] = '\0'; free(got); }
    *bin_size = file_size(bin_path);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

int main(int argc, char **argv)
{
    char exe[1024], run_dir[1024];
    char out_text[8192], lst_text[8192];
    int rc, bin_size;

    if (argc < 2) {
        fprintf(stderr, "usage: test_palbart <package_root>\n");
        return 2;
    }
    if (!realpath(argv[1], exe)) {
        fprintf(stderr, "FATAL: package root not found: %s\n", argv[1]);
        return 2;
    }
    /* 拼出绝对路径的 bin/palbart：子进程会 chdir 到 run_dir，相对路径会失效。 */
    {
        size_t n = strlen(exe);
        if (n + 12 >= sizeof(exe)) { fprintf(stderr, "FATAL: path too long\n"); return 2; }
        strcpy(exe + n, "/bin/palbart");
    }
    if (access(exe, X_OK) != 0) {
        fprintf(stderr, "FATAL: palbart not executable at %s\n", exe);
        return 2;
    }
    snprintf(run_dir, sizeof(run_dir), "palbart_run");
    mkdir(run_dir, 0755);

    /* ---- 用例 A：不给输入文件 ---- */
    printf("== A: no input file ==\n");
    rc = run_palbart(exe, run_dir, NULL, 0, out_text, sizeof(out_text),
                     lst_text, sizeof(lst_text), &bin_size);
    okf(rc == 255, "A1 exit status is 255 -> %ld", rc, 255);
    ok(strstr(out_text, "no input file specified") != NULL,
       "A2 diagnostic says 'no input file specified'");
    ok(bin_size == -1,
       "A3 no .bin produced when input is missing");

    /* ---- 用例 B：完整字模 4 定义 + 字面文本 + 收尾伪操作 ---- */
    printf("== B: valid module 4 ==\n");
    rc = run_palbart(exe, run_dir, "*4 2 100 50\n$HELLO\n*0 5\n", 1,
                     out_text, sizeof(out_text), lst_text, sizeof(lst_text), &bin_size);
    okf(rc == 0, "B1 exit status is 0 -> %ld", rc, 0);
    ok(strstr(lst_text, "*4 2 100 50") != NULL,
       "B2 listing echoes the module-4 pseudo-op");
    ok(strstr(lst_text, "Page 1") != NULL,
       "B3 listing opens a page-1 banner");
    ok(strstr(lst_text, "00004  0152") != NULL,
       "B4 listing reports the .bin offset 00004 and length 0152");
    ok(strstr(lst_text, "$HELLO") != NULL,
       "B5 listing echoes the $-prefixed literal text");
    ok(strstr(lst_text, "No detected errors") != NULL,
       "B6 listing says 'No detected errors'");
    ok(strstr(lst_text, "No links generated") != NULL,
       "B7 listing says 'No links generated'");
    okf(bin_size == 256, "B8 .bin bitstream is 256 bytes -> %ld", bin_size, 256);

    /* ---- 用例 C：未定义符号 + 缺 $ 收尾 → 两条诊断 ---- */
    printf("== C: undefined symbol + unterminated literal ==\n");
    rc = run_palbart(exe, run_dir, "*4 2 100 50\nHELLO\n*0 5\n", 1,
                     out_text, sizeof(out_text), lst_text, sizeof(lst_text), &bin_size);
    okf(rc == 1, "C1 exit status is 1 on detected errors -> %ld", rc, 1);
    ok(strstr(lst_text, "UD undefined") != NULL,
       "C2 listing flags the undefined symbol as 'UD undefined'");
    ok(strstr(lst_text, "ND no $ at EOF") != NULL,
       "C3 listing flags the unterminated literal as 'ND no $ at EOF'");
    ok(strstr(out_text, "2 detected errors") != NULL,
       "C4 stdout summarises '2 detected errors' (plural)");
    ok(strstr(lst_text, "No detected errors") == NULL,
       "C5 listing does NOT claim a clean parse");
    okf(bin_size == 262, "C6 error records still emit 262 .bin bytes -> %ld", bin_size, 262);

    /* ---- 用例 D：省略 *0 5 收尾，解释器自动补页 ---- */
    printf("== D: module 4 without trailing *0 5 ==\n");
    rc = run_palbart(exe, run_dir, "*4 2 100 50\n$HELLO\n", 1,
                     out_text, sizeof(out_text), lst_text, sizeof(lst_text), &bin_size);
    okf(rc == 0, "D1 exit status is 0 without *0 5 -> %ld", rc, 0);
    ok(strstr(lst_text, "No detected errors") != NULL,
       "D2 listing still reports a clean parse");
    okf(bin_size == 256, "D3 .bin matches the terminated run (256 bytes) -> %ld", bin_size, 256);

    /* ---- 用例 E：空输入 ---- */
    printf("== E: empty description file ==\n");
    rc = run_palbart(exe, run_dir, "", 1, out_text, sizeof(out_text),
                     lst_text, sizeof(lst_text), &bin_size);
    okf(rc == 1, "E1 exit status is 1 on empty input -> %ld", rc, 1);
    ok(strstr(out_text, "1 detected error") != NULL,
       "E2 stdout reports '1 detected error' (singular, unlike C4)");
    ok(strstr(lst_text, "ND no $ at EOF") != NULL,
       "E3 listing flags the empty page as 'ND no $ at EOF'");

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
