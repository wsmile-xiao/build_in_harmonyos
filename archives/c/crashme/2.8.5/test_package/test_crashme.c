/* test_package/test_crashme.c — crashme 2.8.5 消费者测试
 *
 * 被测对象是「故意制造崩溃」的健壮性测试工具，因此运行时断言必须**避开崩溃路径**：
 *   T1 bin/crashme 与 bin/pddet 存在
 *   T2 两者可执行
 *   T3 两者均为 ELF64 / AArch64（目标架构正确）
 *   T4 crashme 静态校验产物文件名与权限（不执行崩溃路径）
 *   T5 pddet 被安全调用（-h/无参的默认分支，源自上游 makefile 的 ptest1 目标），
 *      断言进程未被信号杀死、退出码不在 126/127/255（即动态链接与加载器 OK）
 *
 * 不写 /tmp：OHOS 的 /tmp 只读，中间文件落盘会导致误报；这里用 popen 直读输出。
 *
 * 用法: test_crashme <crashme_bin> <pddet_bin>
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

/* 执行并判定"是否安全加载"：未被信号杀死 + 退出码不是 126/127/255 */
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");
    if (!fp) { *code = -1; *killed = 0; return -1; }
    /* P3: 循环读干管道 —— 单次 fread 后在输出超过缓冲时立即 pclose，
     * 会让子进程因写端被关而收到 SIGPIPE（假通过）或阻塞死锁。 */
    size_t n = 0, got;
    while (n < outlen - 1 &&
           (got = fread(out + n, 1, outlen - 1 - n, fp)) > 0) {
        n += got;
    }
    out[n] = '\0';
    int rc = pclose(fp);
    if (rc == -1) { *code = -1; *killed = 0; return -2; }
    *killed = !WIFEXITED(rc);
    *code = *killed ? -1 : WEXITSTATUS(rc);
    if (*killed) return -3;
    /* P2: popen 经 /bin/sh 中转：被信号杀死的子进程由 shell 转成 128+signum
     * （SIGSEGV→139、SIGABRT→134）**正常退出**，因此 WIFEXITED 恒为真、
     * WEXITSTATUS 看不出信号死亡。必须把 126/127 与 >=128 一并判为异常。 */
    if (*code == 126 || *code == 127 || *code >= 128) return -4;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        printf("FAIL test_crashme: missing args (need <crashme> <pddet>)\n");
        return 2;
    }
    const char *crashme = argv[1];
    const char *pddet = argv[2];

    /* ── T1 / T2 ── */
    expect(access(crashme, F_OK) == 0, "T1 crashme present", "(missing)");
    expect(access(crashme, X_OK) == 0, "T2 crashme executable", "(no +x)");
    expect(access(pddet, F_OK) == 0, "T1 pddet present", "(missing)");
    expect(access(pddet, X_OK) == 0, "T2 pddet executable", "(no +x)");

    /* ── T3: 架构 ── */
    char ed[96];
    expect(check_elf(crashme, ed, sizeof(ed)), "T3 crashme is ELF64/AArch64", ed);
    expect(check_elf(pddet, ed, sizeof(ed)), "T3 pddet is ELF64/AArch64", ed);

    /* ── T4: crashme 产物自检（不执行崩溃路径） ──
     * crashme 无 --version/--help，且其设计目的就是制造 SIGSEGV/SIGILL，
     * 故这里只做静态校验：可读、非空、可执行位已置。 */
    FILE *fp = fopen(crashme, "rb");
    int readable = 0;
    if (fp) { fseek(fp, 0, SEEK_END); readable = ftell(fp) > 4096; fclose(fp); }
    expect(readable, "T4 crashme is a non-trivial readable binary", "(read/size check failed)");

    /* ── T5: pddet 安全调用（上游 makefile ptest1 就是直接 ./pddet） ── */
    char out[4096];
    int code = 0, killed = 0;
    int r = safe_run(pddet, out, sizeof(out), &code, &killed);
    char detail[240];
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.90s)", r, killed, code, out);
    expect(r == 0, "T5 pddet loads and runs (not killed / not 126-127-255)", detail);

    printf("test crashme 2.8.5: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
