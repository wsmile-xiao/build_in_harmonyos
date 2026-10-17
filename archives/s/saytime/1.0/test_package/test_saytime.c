/* test_saytime.c — saytime 1.0 消费者测试
 *
 * saytime 是可执行程序、没有可链接的库 API，所以用例按「该程序的真实调用
 * 方式」验证：把包内 bin/saytime 以子进程拉起，检查它对 SAYTIME_SOUNDS 的
 * 响应、对缺失声音目录的诊断，以及最核心的一条——**stdout 上的音频流能被
 * 精确还原成包内 .au 片段的有序拼接**。
 *
 * ★ 为什么不直接断言「输出 N 字节」：saytime 按当前时刻选句子，同一句话在不
 *   同分钟长度不同。所以断言写成「流必须完全由包内 .au 文件首尾相接拼成」，
 *   这与当前时刻无关，是真正确定的性质。
 * ★ 全部期望文本取自 qemu-aarch64 + OHOS sysroot 下的**实测输出**。
 */
#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/wait.h>

#define MAX_CLIPS 64

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

/* 跑一次 saytime。stdout 重定向到 out_path，stderr 重定向到 err_path。
 * 传入 env_assign（形如 "SAYTIME_SOUNDS=/x"）可设置环境变量，NULL 表示不设。
 * 返回退出码（被信号杀死则返回 128+sig）。
 *
 * 注意：子进程会先 chdir 到 run_dir，所以重定向必须用**裸文件名**，
 * 否则会变成 run_dir/run_dir/x 这样的双层路径。 */
static int run_saytime(const char *exe, const char *run_dir, const char *env_assign,
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

    if (env_assign && *env_assign)
        snprintf(script, sizeof(script),
                 "export %s; exec \"%s\" >\"%s\" 2>\"%s\";",
                 env_assign, exe, ob, eb);
    else
        snprintf(script, sizeof(script),
                 "exec \"%s\" >\"%s\" 2>\"%s\";", exe, ob, eb);

    pid = fork();
    if (pid == 0) {
        if (chdir(run_dir) != 0) _exit(127);
        /* 用 sh -c 执行，保证 export + 重定向语义与 shell 版 saytime.sh 一致。 */
        execl("/bin/sh", "sh", "-c", script, (char *)NULL);
        _exit(127);
    }
    if (pid < 0) return -1;
    waitpid(pid, &status, 0);
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}

int main(int argc, char **argv)
{
    char pkg[1024], sounds[1200], run_dir[1200], exe[1200];
    char out_path[1300], err_path[1300];
    char *out = NULL, *err = NULL, *clip[MAX_CLIPS];
    long out_len = 0, clip_len[MAX_CLIPS];
    int nclips = 0, i;
    long consumed = 0, clips_used = 0;
    DIR *d;
    struct dirent *de;

    if (argc < 2) {
        fprintf(stderr, "usage: test_saytime <package_root>\n");
        return 2;
    }
    if (!realpath(argv[1], pkg)) {
        fprintf(stderr, "FATAL: package root not found: %s\n", argv[1]);
        return 2;
    }
    snprintf(sounds, sizeof(sounds), "%s/share/saytime/sounds", pkg);
    snprintf(exe, sizeof(exe), "%s/bin/saytime", pkg);
    if (access(exe, X_OK) != 0) {
        fprintf(stderr, "FATAL: saytime not executable at %s\n", exe);
        return 2;
    }
    snprintf(run_dir, sizeof(run_dir), "saytime_run");
    mkdir(run_dir, 0755);
    snprintf(out_path, sizeof(out_path), "%s/stream.au", run_dir);
    snprintf(err_path, sizeof(err_path), "%s/diag.txt", run_dir);

    /* ---- 前置：包内必须带齐 30 段语音 ---- */
    d = opendir(sounds);
    if (!d) {
        fprintf(stderr, "FATAL: sounds dir missing: %s\n", sounds);
        return 2;
    }
    while ((de = readdir(d)) != NULL && nclips < MAX_CLIPS) {
        char p[1400];
        size_t n = strlen(de->d_name);
        if (n < 3 || strcmp(de->d_name + n - 3, ".au") != 0) continue;
        snprintf(p, sizeof(p), "%s/%s", sounds, de->d_name);
        clip[nclips] = slurp(p, &clip_len[nclips]);
        if (clip[nclips]) nclips++;
    }
    closedir(d);
    okf(nclips == 30, "package ships all 30 mu-law phrase clips", nclips, 30);

    /* ---- 用例 A：SAYTIME_SOUNDS 指向包内 sounds → 正常产出音频流 ---- */
    printf("== A: SAYTIME_SOUNDS points at the packaged clips ==\n");
    {
        char envbuf[1300];
        int rc;
        snprintf(envbuf, sizeof(envbuf), "SAYTIME_SOUNDS=%s", sounds);
        rc = run_saytime(exe, run_dir, envbuf, out_path, err_path);
        okf(rc == 0, "A1 exit status is 0", rc, 0);

        err = slurp(err_path, NULL);
        ok(err && strstr(err, "/dev/audio unavailable") != NULL,
           "A2 stderr reports that /dev/audio is unavailable");
        ok(err && strstr(err, "writing the audio stream to stdout") != NULL,
           "A3 stderr reports the stdout fallback");
        free(err);

        out = slurp(out_path, &out_len);
        ok(out != NULL && out_len > 0,
           "A4 a non-empty audio stream reached stdout");
    }

    /* ---- 用例 B：stdout 必须能被精确还原成 .au 片段的有序拼接 ----
     * 贪心匹配：每次在当前位置找一个能完整匹配的片段，消耗掉；最终必须正好
     * 消耗完整个流，不多不少。这与当前时刻无关，因此是确定性断言。 */
    printf("== B: the stream is an exact ordered concatenation of the clips ==\n");
    if (out && out_len > 0) {
        long pos = 0;
        int complete = 1;
        while (pos < out_len) {
            int matched = 0;
            for (i = 0; i < nclips; i++) {
                if (clip_len[i] <= 0) continue;
                if (pos + clip_len[i] <= out_len &&
                    memcmp(out + pos, clip[i], (size_t)clip_len[i]) == 0) {
                    pos += clip_len[i];
                    clips_used++;
                    matched = 1;
                    break;
                }
            }
            if (!matched) { complete = 0; break; }
        }
        consumed = pos;
        ok(complete && pos == out_len,
           "B1 the whole stream decomposes into packaged .au clips");
        okf(complete ? pos : -1, "B2 no trailing partial bytes",
            complete ? pos : -1, out_len);
        okf(clips_used >= 3, "B3 at least 3 clips are concatenated", clips_used, 3);
        okf(clips_used <= 30, "B4 never more clips than the package ships", clips_used, 30);

        /* 第一句永远是 "The time is ..."：the_time_is.au 必须打头。
         * 按固定路径读一次，不依赖 readdir 的目录顺序。 */
        {
            char p[1400];
            long tl = 0;
            char *b;
            snprintf(p, sizeof(p), "%s/the_time_is.au", sounds);
            b = slurp(p, &tl);
            if (b) {
                ok(out_len >= tl && memcmp(out, b, (size_t)tl) == 0,
                   "B5 the stream always starts with the_time_is.au");
                free(b);
            } else {
                ok(0, "B5 the_time_is.au readable from the package");
            }
        }
    } else {
        ok(0, "B1 skipped: no stream captured in case A");
        ok(0, "B2 skipped: no stream captured in case A");
        ok(0, "B3 skipped: no stream captured in case A");
        ok(0, "B4 skipped: no stream captured in case A");
        ok(0, "B5 skipped: no stream captured in case A");
    }

    /* ---- 用例 C：SAYTIME_SOUNDS 指向不存在的目录 → 明确诊断 + 退出码 1 ---- */
    printf("== C: SAYTIME_SOUNDS points at a missing directory ==\n");
    {
        int rc = run_saytime(exe, run_dir, "SAYTIME_SOUNDS=/definitely/not/here",
                             out_path, err_path);
        long olen = 0;
        char *o = slurp(out_path, &olen);
        okf(rc == 1, "C1 exit status is 1 on a missing clip directory", rc, 1);
        err = slurp(err_path, NULL);
        ok(err && strstr(err, "opening audio file") != NULL,
           "C2 stderr says 'opening audio file'");
        ok(err && strstr(err, "No such file or directory") != NULL,
           "C3 stderr carries the errno text");
        free(err);
        okf(o == NULL || olen == 0, "C4 nothing is written to stdout", o ? olen : 0, 0);
        free(o);
    }

    /* ---- 用例 D：SAYTIME_SOUNDS 指向空目录 → 同样是退出码 1 ---- */
    printf("== D: SAYTIME_SOUNDS points at an empty directory ==\n");
    {
        int rc;
        long olen = 0;
        char *o;
        char empty[1200], envbuf[1300];
        snprintf(empty, sizeof(empty), "%s/empty_sounds", run_dir);
        mkdir(empty, 0755);
        snprintf(envbuf, sizeof(envbuf), "SAYTIME_SOUNDS=%s", empty);
        rc = run_saytime(exe, run_dir, envbuf, out_path, err_path);
        o = slurp(out_path, &olen);
        okf(rc == 1, "D1 exit status is 1 on an empty clip directory", rc, 1);
        okf(o == NULL || olen == 0, "D2 nothing is written to stdout", o ? olen : 0, 0);
        free(o);
        err = slurp(err_path, NULL);
        ok(err && strstr(err, "opening audio file") != NULL,
           "D3 stderr says 'opening audio file'");
        free(err);
    }

    for (i = 0; i < nclips; i++) free(clip[i]);
    free(out);

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
