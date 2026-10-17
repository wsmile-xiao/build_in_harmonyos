/* test_package/test_cvs_fast_export.c — cvs-fast-export 1.59 消费者测试
 *
 * 消费包内产物：
 *   T1 cvs-fast-export 存在且可执行
 *   T2 ELF64 / AArch64
 *   T3 `-V` 真实执行：未被信号杀死、未落在 126/127/128+，且输出含源码版本文面 "version"
 *      （main.c: printf("%s: version " VERSION "\n", argv[0]) ）
 *   T4 `-h` 真实执行：同样排除加载失败码，且输出含源码 usage 字面 "Usage:"
 *      （main.c: printf("Usage: cvs-fast-export [OPTIONS] [FILE]...\n" ...) ）
 *   T5 上游附带的三个 Python 辅助脚本存在且可执行
 *
 * 判据说明（P2/P3 加固）：
 *   - popen 经 /bin/sh 中转：被信号杀死的子进程由 shell 转成 128+signum（SIGSEGV→139、
 *     SIGABRT→134）**正常退出**，WIFEXITED 恒为真 —— 因此判据必须把 126/127 与 >=128
 *     一并视为"没跑起来"，不能只看 WIFEXITED。
 *   - 循环读干管道才 pclose：单次 fread 后在输出超过缓冲时立即关闭，会让子进程
 *     收到 SIGPIPE（假通过）或阻塞死锁。
 *   - 不写 /tmp：OHOS 上 /tmp 只读，中间文件落盘会让判据凭空失败。
 *
 * 用法: test_cfe <bin_dir>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

static int passed = 0, failed = 0;

static void expect(int cond, const char *name, const char *detail) {
    if (cond) { printf("PASS %s\n", name); passed++; }
    else { printf("FAIL %s %s\n", name, detail ? detail : ""); failed++; }
}

static int check_elf(const char *path, char *d, size_t n) {
    FILE *fp = fopen(path, "rb");
    if (!fp) { snprintf(d, n, "(unreadable)"); return 0; }
    unsigned char h[20];
    size_t got = fread(h, 1, sizeof(h), fp);
    fclose(fp);
    if (got < 20 || h[0] != 0x7f || h[1] != 'E' || h[2] != 'L' || h[3] != 'F') {
        snprintf(d, n, "(not ELF)");
        return 0;
    }
    unsigned int machine = (unsigned int)h[18] | ((unsigned int)h[19] << 8);
    if (h[4] != 2 || machine != 0xB7) {
        snprintf(d, n, "(elfclass=%u machine=0x%X want 2/0xB7)", h[4], machine);
        return 0;
    }
    snprintf(d, n, "(ELF64/AArch64)");
    return 1;
}

/* 执行并判定"是否安全加载"；返回 0 表示跑起来了 */
static int safe_run(const char *path, const char *args, char *out, size_t outlen,
                    int *code, int *killed) {
    char cmd[1400];
    if (args && *args)
        snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", path, args);
    else
        snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");
    if (!fp) { *code = -1; *killed = 0; return -1; }
    size_t n = 0, got;
    while (n < outlen - 1 && (got = fread(out + n, 1, outlen - 1 - n, fp)) > 0)
        n += got;
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);
    *code = *killed ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    if (*code == 126 || *code == 127 || *code >= 128) return -4;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_cfe: missing <bin_dir> argument\n");
        return 2;
    }
    const char *dir = argv[1];
    char path[1200], out[4096], ed[96], detail[260];
    int code, killed, r;

    snprintf(path, sizeof(path), "%s/cvs-fast-export", dir);
    expect(access(path, F_OK) == 0, "T1 cvs-fast-export present", "(missing)");
    expect(access(path, X_OK) == 0, "T1 cvs-fast-export executable", "(no +x)");
    expect(check_elf(path, ed, sizeof(ed)), "T2 cvs-fast-export is ELF64/AArch64", ed);

    /* T3: -V -> main.c 的 printf("%s: version " VERSION "\n", argv[0]) */
    code = 0; killed = 0;
    r = safe_run(path, "-V", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.100s)", r, killed, code, out);
    expect(r == 0, "T3 -V runs (not killed / not 126-127-128+)", detail);
    expect(strstr(out, "version") != NULL, "T3 -V prints version string", detail);

    /* T4: -h -> main.c 的 printf("Usage: cvs-fast-export [OPTIONS] [FILE]...\n" ...) */
    code = 0; killed = 0;
    r = safe_run(path, "-h", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.100s)", r, killed, code, out);
    expect(r == 0, "T4 -h runs (not killed / not 126-127-128+)", detail);
    expect(strstr(out, "Usage") != NULL, "T4 -h prints usage", detail);

    /* T5: 上游附带的 Python 辅助脚本 */
    const char *helpers[3] = { "cvsconvert", "cvsstrip", "cvssync" };
    int i;
    for (i = 0; i < 3; i++) {
        snprintf(path, sizeof(path), "%s/%s", dir, helpers[i]);
        snprintf(detail, sizeof(detail), "(%s missing)", helpers[i]);
        expect(access(path, F_OK) == 0 && access(path, X_OK) == 0,
               i == 0 ? "T5 cvsconvert present+executable" :
               i == 1 ? "T5 cvsstrip present+executable" :
                        "T5 cvssync present+executable", detail);
    }

    printf("test cvs-fast-export 1.59: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
