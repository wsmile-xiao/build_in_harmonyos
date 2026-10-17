/* test_package/test_daa2iso.c — daa2iso 0.1.7e 消费者测试
 *
 * daa2iso 是 CLI 工具（非库），直接消费包内 bin/daa2iso：
 *   T1 bin/daa2iso 存在且可执行
 *   T2 ELF64 / AArch64（目标架构正确）
 *   T3 真实执行：rc 有效（非 -1）、未被信号杀死、退出码不在 126/127 且 < 128
 *   T4 无参数时打印 "Usage: ..."（源码 argc<3 分支的确切输出）
 *
 * 不写 /tmp：OHOS 的 /tmp 只读，中间文件落盘会导致误报；这里用 popen 直读输出。
 *
 * 用法: test_daa2iso <daa2iso_binary>
 */
/* ★ 特性测试宏必须在所有 #include 之前（popen/pclose/access/WIFEXITED 属 POSIX，
 * 严格 ISO C 方言下 glibc 与 musl 都会隐藏其声明，导致指针截断、运行时段错误）。 */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

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

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_daa2iso: missing <daa2iso_binary> argument\n");
        return 2;
    }
    const char *bin = argv[1];

    expect(access(bin, F_OK) == 0, "T1 daa2iso present", "(missing)");
    expect(access(bin, X_OK) == 0, "T1 daa2iso executable", "(no +x)");

    char ed[96];
    expect(check_elf(bin, ed, sizeof(ed)), "T2 daa2iso is ELF64/AArch64", ed);

    char cmd[1200];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", bin);
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        expect(0, "T3 daa2iso runs", "(popen failed)");
        expect(0, "T4 prints usage", "(popen failed)");
        printf("test daa2iso 0.1.7e: %d passed, %d failed\n", passed, failed);
        return 1;
    }
    char out[4096];
    /* P3: 循环读干管道 —— 单次 fread 后在输出超过缓冲时立即 pclose，
     * 会让子进程因写端被关而收到 SIGPIPE（假通过）或阻塞死锁。 */
    size_t n = 0, got;
    while (n < sizeof(out) - 1 &&
           (got = fread(out + n, 1, sizeof(out) - 1 - n, fp)) > 0) {
        n += got;
    }
    out[n] = '\0';
    int rc = pclose(fp);

    /* ★ 完整「跑不起来」过滤（吸收 AI 检视 P2）：
     * 旧写法 `code = (rc == -1) ? -1 : WEXITSTATUS(rc); killed = (rc != -1) && !WIFEXITED(rc);`
     * 配 `!killed && code < 126` 有漏洞：rc == -1（waitpid 本身失败）时
     * killed 为 false、code = -1 < 126，判据反而 **PASS**，把管道/进程异常当成通过。
     * 统一为显式 run_failed：
     *   - rc == -1            → waitpid 失败
     *   - !WIFEXITED(rc)      → 子进程被信号杀死（脚本场景）
     *   - 126 / 127           → exec 失败 / 命令未找到
     *   - >= 128              → popen 经 /bin/sh 中转时 shell 把信号死亡转成
     *                           128+signum（SIGSEGV→139、SIGABRT→134）后正常退出
     */
    int killed = (rc != -1) && !WIFEXITED(rc);
    int code = (rc == -1 || killed) ? -1 : WEXITSTATUS(rc);
    int run_failed = (rc == -1) || killed ||
                     code == 126 || code == 127 || code >= 128;

    char detail[240];
    snprintf(detail, sizeof(detail), "(rc=%d killed=%d code=%d bytes=%zu out=%.80s)",
             rc, killed, code, n, out);
    expect(!run_failed,
           "T3 daa2iso runs (not rc==-1 / not killed / not 126-127-128+)", detail);
    expect(strstr(out, "Usage") != NULL, "T4 prints usage on empty args", detail);

    printf("test daa2iso 0.1.7e: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
