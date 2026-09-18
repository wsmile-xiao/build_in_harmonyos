/* test_package/test_dds2tar.c — dds2tar 2.5.2 消费者测试
 *
 * 消费包内三个产物：
 *   T1 dds2tar / dds2index / ddstool 存在
 *   T2 三者可执行
 *   T3 dds2tar 与 dds2index 是 ELF64/AArch64
 *   T4 dds2tar 真实执行（无参数）：未被信号杀死、退出码不在 126/127/255
 *   T5 dds2tar 输出非空（无参数时的 usage/提示路径）
 *   T6 dds2index 真实执行（-h 或空参）：同样排除加载失败码
 *
 * 不写 /tmp：OHOS 上 /tmp 只读，中间文件落盘会让判据凭空失败；用 popen 直读。
 *
 * 用法: test_dds2tar <dds2tar> <dds2index> <ddstool>
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

static int safe_run(const char *path, const char *args, char *out, size_t outlen,
                    int *code, int *killed) {
    char cmd[1400];
    if (args && *args)
        snprintf(cmd, sizeof(cmd), "\"%s\" %s < /dev/null 2>&1", path, args);
    else
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
    if (argc < 4) {
        printf("FAIL test_dds2tar: missing args (need <dds2tar> <dds2index> <ddstool>)\n");
        return 2;
    }
    const char *tar_bin = argv[1], *index_bin = argv[2], *tool_bin = argv[3];

    expect(access(tar_bin, F_OK) == 0, "T1 dds2tar present", "(missing)");
    expect(access(tar_bin, X_OK) == 0, "T2 dds2tar executable", "(no +x)");
    expect(access(index_bin, F_OK) == 0, "T1 dds2index present", "(missing)");
    expect(access(index_bin, X_OK) == 0, "T2 dds2index executable", "(no +x)");
    expect(access(tool_bin, F_OK) == 0, "T1 ddstool present", "(missing)");
    expect(access(tool_bin, X_OK) == 0, "T2 ddstool executable", "(no +x)");

    char ed[96];
    expect(check_elf(tar_bin, ed, sizeof(ed)), "T3 dds2tar is ELF64/AArch64", ed);
    expect(check_elf(index_bin, ed, sizeof(ed)), "T3 dds2index is ELF64/AArch64", ed);

    char out[4096];
    int code = 0, killed = 0, r;
    char detail[240];

    /* T4：无参数执行 —— 真机实测 dds2tar 无参数时**静默 exit 0 且无输出**，
     * 因此这里只断言「跑起来了」（未被信号杀死、非 126/127/255），不断言有输出。 */
    r = safe_run(tar_bin, "", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.80s)", r, killed, code, out);
    expect(r == 0, "T4 dds2tar runs (not killed / not 126-127-255)", detail);

    /* T5：`-V` 走源码 dds2tar.c 的
     *     fprintf(stdout, "%s: %s\n", pg, version);  （version[] = "Version " VERSION " ..."）
     * —— 这是源码里确定会输出的字面量，用它做语义断言（而不是假设"无参数会打印 usage"）。 */
    code = 0; killed = 0;
    r = safe_run(tar_bin, "-V", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.90s)", r, killed, code, out);
    expect(r == 0, "T5 dds2tar -V runs (not killed / not 126-127-255)", detail);
    expect(strstr(out, "Version") != NULL, "T5 dds2tar -V prints version string", detail);

    code = 0; killed = 0;
    r = safe_run(index_bin, "-h", out, sizeof(out), &code, &killed);
    snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.80s)", r, killed, code, out);
    expect(r == 0, "T6 dds2index runs (not killed / not 126-127-255)", detail);

    printf("test dds2tar 2.5.2: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
