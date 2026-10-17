/* test_package/test_cpmtools.c — cpmtools 2.23 消费者测试
 *
 * 消费包内 7 个 CP/M 工具（cpmls/cpmrm/cpmcp/cpmchmod/cpmchattr/mkfs.cpm/fsck.cpm）：
 *   1) 逐个断言：存在 + 可执行
 *   2) 抽样断言 ELF64/AArch64（每个工具单独判定，便于定位）
 *   3) 逐个真实执行（`-h` / 无参数）：未被信号杀死、退出码不在 126/127/255
 *      —— cpmtools 的参数解析走自带 getopt，无参数时打印 usage 并返回非 0，属预期
 *
 * 不写 /tmp：OHOS 上 /tmp 只读，中间文件落盘会让判据凭空失败；用 popen 直读。
 *
 * 用法: test_cpmtools <bin_dir>          （bin_dir 下按名字取 7 个工具）
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#define NTOOL 7

static const char *TOOLS[NTOOL] = {
    "cpmls", "cpmrm", "cpmcp", "cpmchmod", "cpmchattr", "mkfs.cpm", "fsck.cpm"
};

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

/* 真实执行并判定"是否安全加载"：未被信号杀死 + 退出码不是 126/127/255 */
static int safe_run(const char *path, char *out, size_t outlen, int *code, int *killed) {
    char cmd[1400];
    snprintf(cmd, sizeof(cmd), "\"%s\" -h < /dev/null 2>&1", path);
    FILE *fp = popen(cmd, "r");
    if (!fp) { *code = -1; *killed = 0; return -1; }
    /* P3: 循环读干管道 —— 单次 fread 后在输出超过缓冲时立即 pclose，
     * 会让子进程因写端被关而收到 SIGPIPE（假通过/死锁）。 */
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
    /* P2: popen 经 /bin/sh 中转，被信号杀死的子进程由 shell 转成 128+signum
     * （如 SIGSEGV→139、SIGABRT→134）**正常退出**，因此 WIFEXITED 恒为真、
     * WEXITSTATUS 看不出信号死亡。必须把 126/127 与 >=128 一并判为异常。 */
    if (*code == 126 || *code == 127 || *code >= 128) return -4;
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_cpmtools: missing <bin_dir> argument\n");
        return 2;
    }
    const char *dir = argv[1];
    char path[1200], name[160], out[4096], ed[96], detail[240];
    int i, code, killed, r;

    for (i = 0; i < NTOOL; i++) {
        snprintf(path, sizeof(path), "%s/%s", dir, TOOLS[i]);
        snprintf(name, sizeof(name), "T1 %s present", TOOLS[i]);
        expect(access(path, F_OK) == 0, name, "(missing)");
        snprintf(name, sizeof(name), "T2 %s executable", TOOLS[i]);
        expect(access(path, X_OK) == 0, name, "(no +x)");
    }

    for (i = 0; i < NTOOL; i++) {
        snprintf(path, sizeof(path), "%s/%s", dir, TOOLS[i]);
        if (!check_elf(path, ed, sizeof(ed))) {
            snprintf(name, sizeof(name), "T3 %s is ELF64/AArch64", TOOLS[i]);
            expect(0, name, ed);
        }
    }
    /* 若全部通过，合并汇报一条（避免 7 条重复 PASS 刷屏） */
    {
        int allok = 1;
        for (i = 0; i < NTOOL; i++) {
            snprintf(path, sizeof(path), "%s/%s", dir, TOOLS[i]);
            if (!check_elf(path, ed, sizeof(ed))) allok = 0;
        }
        if (allok) expect(1, "T3 all 7 tools are ELF64/AArch64", ed);
    }

    for (i = 0; i < NTOOL; i++) {
        snprintf(path, sizeof(path), "%s/%s", dir, TOOLS[i]);
        code = 0; killed = 0;
        r = safe_run(path, out, sizeof(out), &code, &killed);
        snprintf(detail, sizeof(detail), "(r=%d killed=%d rc=%d out=%.70s)", r, killed, code, out);
        snprintf(name, sizeof(name), "T4 %s runs (not killed / not 126-127-255)", TOOLS[i]);
        expect(r == 0, name, detail);
    }

    printf("test cpmtools 2.23: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
