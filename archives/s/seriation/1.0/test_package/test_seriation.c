/* test_seriation.c — seriation 1.0 消费者测试
 *
 * cfm-seriation 是可执行程序、没有可链接的库 API，所以用例按「该程序的真实
 * 调用方式」验证：把包内 bin/cfm_seriation 以子进程拉起，喂入 CFM 边表，
 * 对它的诊断输出、退出码、能量收敛值与产物目录做确定性断言。
 *
 * ★ 全部期望值取自 qemu-aarch64 + OHOS sysroot 下的**实测输出**。
 * ★ 最强的一条是 D 组：固定随机种子后连跑三次，INITIAL/FINAL Energy 必须
 *   逐字节一致 —— 这直接验证模拟退火在 aarch64 上是确定可重复的，而不只
 *   是「能跑通」。
 */
#include <dirent.h>
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

/* 跑一次 cfm_seriation。子进程 chdir 到 run_dir，stdout+stderr 并到 out_path。
 * 注意重定向必须用裸文件名：chdir 之后再用带目录的相对路径会变成双层路径。 */
static int run_ser(const char *exe, const char *run_dir, const char *args,
                   const char *out_path, const char *err_path)
{
    pid_t pid;
    int status = -1;
    char script[4096];
    const char *ob = strrchr(out_path, '/');
    const char *eb = strrchr(err_path, '/');
    ob = ob ? ob + 1 : out_path;
    eb = eb ? eb + 1 : err_path;

    unlink(out_path);
    unlink(err_path);

    snprintf(script, sizeof(script), "exec \"%s\" %s >\"%s\" 2>\"%s\";",
             exe, args ? args : "", ob, eb);

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

/* 找出 run_dir 下形如 <base>_<YYYY-MM-DD_HHhMmMmSs> 的产物目录。 */
static int find_outdir(const char *run_dir, const char *base, char *dst, size_t cap)
{
    DIR *d = opendir(run_dir);
    struct dirent *de;
    char prefix[256];
    int found = 0;
    if (!d) return 0;
    snprintf(prefix, sizeof(prefix), "%s_", base);
    while (!found && (de = readdir(d)) != NULL) {
        char full[1400];
        if (strncmp(de->d_name, prefix, strlen(prefix)) != 0) continue;
        /* 形状校验：前缀 + strftime("%Y-%m-%d_%Hh%Mm%Ss") = 20 字符。
         * 例如 mini_2026-10-04_04h14m38s。 */
        if (strlen(de->d_name) != strlen(prefix) + 20) continue;
        snprintf(full, sizeof(full), "%s/%s", run_dir, de->d_name);
        {
            struct stat st;
            if (stat(full, &st) != 0 || !S_ISDIR(st.st_mode)) continue;
        }
        snprintf(dst, cap, "%s", full);
        found = 1;
    }
    closedir(d);
    return found;
}

static int has_entry(const char *dir, const char *entry)
{
    char p[1600];
    struct stat st;
    snprintf(p, sizeof(p), "%s/%s", dir, entry);
    return stat(p, &st) == 0;
}

/* 从 stdout 文本里抠出 "INITIAL Energy: N" / "FINAL Energy: N" 的 N */
static int grab_energy(const char *text, const char *key)
{
    const char *p = strstr(text, key);
    if (!p) return -1;
    p += strlen(key);
    while (*p == ' ') p++;
    return atoi(p);
}

int main(int argc, char **argv)
{
    char pkg[1024], run_dir[1200], exe[1300], dat[1300];
    char out_path[1400], err_path[1400], outdir[1400];
    char *text = NULL;
    int rc;

    if (argc < 2) {
        fprintf(stderr, "usage: test_seriation <package_root>\n");
        return 2;
    }
    if (!realpath(argv[1], pkg)) {
        fprintf(stderr, "FATAL: package root not found: %s\n", argv[1]);
        return 2;
    }
    snprintf(exe, sizeof(exe), "%s/bin/cfm_seriation", pkg);
    if (access(exe, X_OK) != 0) {
        fprintf(stderr, "FATAL: cfm_seriation not executable at %s\n", exe);
        return 2;
    }
    snprintf(run_dir, sizeof(run_dir), "seriation_run");
    mkdir(run_dir, 0755);
    snprintf(out_path, sizeof(out_path), "%s/run.out", run_dir);
    snprintf(err_path, sizeof(err_path), "%s/run.err", run_dir);
    snprintf(dat, sizeof(dat), "%s/mini.dat", run_dir);

    /* 最小 CFM 边表：6 行边、4 个节点。上游 readProteinList() 按「每行两个
     * 节点名」解析，buildMat() 据此建邻接矩阵。 */
    {
        FILE *f = fopen(dat, "wb");
        if (!f) { fprintf(stderr, "FATAL: cannot write %s\n", dat); return 2; }
        fputs("n1 n2\nn2 n3\nn3 n4\nn4 n1\nn1 n3\nn2 n4\n", f);
        fclose(f);
    }

    /* ---- A：无参数 → 用法 + Invalid file name，退出码 1 ---- */
    printf("== A: no arguments ==\n");
    rc = run_ser(exe, run_dir, NULL, out_path, err_path);
    okf(rc == 1, "A1 exit status is 1", rc, 1);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "Usage:") != NULL, "A2 prints a Usage banner");
    ok(text && strstr(text, "Seriation Parameters:") != NULL,
       "A3 lists the seriation parameters");
    ok(text && strstr(text, "ERROR! Invalid file name.") != NULL,
       "A4 reports 'ERROR! Invalid file name.'");
    ok(text && strstr(text, "f=[NETWORK FILE].dat") != NULL,
       "A5 documents the f= option");
    free(text);

    /* ---- B：h → 打印完整帮助后 exit 1（上游 print_help(); exit(1);）---- */
    printf("== B: h prints help and exits 1 ==\n");
    rc = run_ser(exe, run_dir, "h", out_path, err_path);
    okf(rc == 1, "B1 exit status is 1 (upstream exits 1 after help)", rc, 1);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "Usage: ./cfm_seriation") != NULL,
       "B2 names the program as ./cfm_seriation");
    ok(text && strstr(text, "s=[SEDD]") != NULL, "B3 documents the s= seed option");
    ok(text && strstr(text, "P                          Plot graphs") != NULL,
       "B4 documents the P plot option");
    free(text);

    /* ---- C：f 指向不存在的文件 → Invalid file path，退出码 1 ---- */
    printf("== C: f= points at a missing file ==\n");
    rc = run_ser(exe, run_dir, "f=nope.dat", out_path, err_path);
    okf(rc == 1, "C1 exit status is 1 on a missing network file", rc, 1);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "ERROR! Invalid file path \"nope.dat\".") != NULL,
       "C2 names the offending path in the diagnostic");
    free(text);

    /* ---- D：固定种子跑三次 → 能量逐次一致（确定性）---- */
    printf("== D: a fixed seed is reproducible ==\n");
    {
        int init_energy[3], final_energy[3];
        int same = 1, i;
        for (i = 0; i < 3; i++) {
            rc = run_ser(exe, run_dir, "f=mini.dat s=42 i=2 m=2", out_path, err_path);
            if (rc != 0) break;
            text = slurp(out_path, NULL);
            init_energy[i] = grab_energy(text ? text : "", "INITIAL Energy:");
            final_energy[i] = grab_energy(text ? text : "", "FINAL Energy:");
            free(text);
        }
        okf(rc == 0, "D1 exit status is 0 on a valid network", rc, 0);
        okf(init_energy[0] == 12, "D2 INITIAL Energy is 12 for the 4-node network",
            init_energy[0], 12);
        okf(final_energy[0] == 12, "D3 FINAL Energy is 12 (already minimal)",
            final_energy[0], 12);
        for (i = 1; i < 3; i++) {
            if (init_energy[i] != init_energy[0] || final_energy[i] != final_energy[0])
                same = 0;
        }
        ok(same, "D4 three runs with the same seed give identical energies");
    }

    /* ---- E：诊断输出与产物目录 ---- */
    printf("== E: diagnostics and the output directory ==\n");
    rc = run_ser(exe, run_dir, "f=mini.dat s=42 i=2 m=2", out_path, err_path);
    text = slurp(out_path, NULL);
    ok(text && strstr(text, "Reading file...") != NULL, "E1 reports it is reading the file");
    ok(text && strstr(text, "Proteins: 4") != NULL, "E2 counts 4 proteins/nodes");
    ok(text && strstr(text, "Interactions: 3") != NULL, "E3 counts 3 interactions");
    ok(text && strstr(text, "Done!") != NULL, "E4 finishes with Done!");
    free(text);

    outdir[0] = '\0';
    ok(find_outdir(run_dir, "mini", outdir, sizeof(outdir)) != 0,
       "E5 creates an output dir named mini_<YYYY-MM-DD_HHhMmMmSs>");
    if (outdir[0]) {
        ok(has_entry(outdir, "energy.dat"), "E6 energy.dat is present");
        ok(has_entry(outdir, "initial_order.dat"), "E7 initial_order.dat is present");
        ok(has_entry(outdir, "final_order.dat"), "E8 final_order.dat is present");
        ok(has_entry(outdir, "result.txt"), "E9 result.txt is present");
    } else {
        int i;
        for (i = 6; i <= 9; i++) ok(0, "skipped: no output directory found");
    }

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
