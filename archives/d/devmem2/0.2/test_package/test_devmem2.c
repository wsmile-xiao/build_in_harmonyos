/* test_package/test_devmem2.c — devmem2 0.2 consumer test
 *
 * devmem2 是 CLI 工具（非库），无 link 目标；本测试直接消费包内 devmem2 二进制：
 *   T1 bin/devmem2 存在且可执行（access X_OK）
 *   T2 真实执行 devmem2（无参数）有输出（证明程序可运行、链接正常）
 *   T3 输出含 "Usage" 提示（对应 devmem2.c 的 usage 分支）
 *
 * 注意：**不要把中间文件写到 /tmp** —— OHOS 上 /tmp 是只读文件系统，
 * 写失败会让 grep 找不到文件而误报（CI 实测报错：
 *   sh: can't create /tmp/devmem2_test.out: Read-only file system）。
 * 这里用 popen 直接读子进程输出，完全不落盘，跨平台一致。
 *
 * 用法: test_devmem2 <devmem2_binary_path>
 */
/* ★ 特性测试宏必须在所有 #include 之前。
 * popen / pclose / access / WIFEXITED 是 POSIX 而非 ISO C；在严格 ISO C 方言
 * （-std=c99/c11，未定义 _POSIX_C_SOURCE）下 glibc 与 musl 都会隐藏 popen/pclose
 * 声明，隐式 int 返回值被赋给 FILE* 会指针截断 —— 编译仅告警、运行必段错误。
 */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

static int passed = 0, failed = 0;

static void ok(const char *name) { printf("PASS %s\n", name); passed++; }
static void fail(const char *name, const char *detail) {
    printf("FAIL %s %s\n", name, detail ? detail : ""); failed++;
}
static void expect(int cond, const char *name, const char *detail) {
    if (cond) ok(name); else fail(name, detail);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("FAIL test_devmem2: missing <devmem2_binary> argument\n");
        return 2;
    }
    const char *devmem2 = argv[1];

    /* ── T1: 存在 + 可执行 ── */
    expect(access(devmem2, F_OK) == 0, "T1 devmem2 binary present", "(missing)");
    expect(access(devmem2, X_OK) == 0, "T1 devmem2 binary executable", "(no +x)");

    /* ── T2/T3: 真实执行，直读输出（不落盘） ── */
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" < /dev/null 2>&1", devmem2);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fail("T2 devmem2 runs and produces output", "(popen failed)");
        fail("T3 output contains 'Usage' prompt", "(popen failed)");
        printf("test devmem2 0.2: %d passed, %d failed\n", passed, failed);
        return 1;
    }
    char buf[4096];
    /* P3: 循环读干管道 —— 单次 fread 后在输出超过缓冲时立即 pclose，
     * 会让子进程因写端被关而收到 SIGPIPE（假通过）或阻塞死锁。 */
    size_t n = 0, got;
    while (n < sizeof(buf) - 1 &&
           (got = fread(buf + n, 1, sizeof(buf) - 1 - n, fp)) > 0) {
        n += got;
    }
    buf[n] = '\0';
    int rc = pclose(fp);

    /* ★ 完整「跑不起来」过滤（吸收 AI 检视 P2）：
     *   - pclose() 返回 -1 表示 waitpid 本身失败，此时 WEXITSTATUS 无意义；
     *   - 子进程被信号杀死时 WIFEXITED(rc) 为假、WEXITSTATUS(rc) 是未定义值，
     *     必须先判 WIFEXITED 再取 WEXITSTATUS；
     *   - popen 经 /bin/sh 中转：shell 会把子进程的信号死亡转成 128+signum
     *     （SIGSEGV→139、SIGABRT→134）后**正常退出**，故 126/127/>=128 一并
     *     视为"没跑起来"。
     * 三者缺一，崩溃或加载失败都会被误判 PASS。
     */
    int killed = !WIFEXITED(rc);
    int exit_code = (rc == -1 || killed) ? -1 : WEXITSTATUS(rc);
    int run_failed = (rc == -1) || killed ||
                     exit_code == 126 || exit_code == 127 || exit_code >= 128;

    char detail[192];
    snprintf(detail, sizeof(detail), "(rc=%d killed=%d exit=%d bytes=%zu output=%.80s)",
             rc, killed, exit_code, n, buf);
    expect(n > 0 && !run_failed,
           "T2 devmem2 runs and produces output (not rc==-1 / not killed / not 126-127-128+)",
           detail);
    expect(strstr(buf, "Usage") != NULL, "T3 output contains 'Usage' prompt", detail);

    printf("test devmem2 0.2: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
