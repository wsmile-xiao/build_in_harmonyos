/* test_package/test_devio.c — devio 1.2 consumer test
 *
 * devio 是 CLI 工具（非库），无 link 目标；本测试直接消费包内 devio 二进制：
 *   T1 bin/devio 存在且可执行（access X_OK）
 *   T2 真实执行 devio（无参数），进程正常启动并返回（非崩溃/加载失败）
 *   T3 输出含 usage/read/write 关键字（证明程序本体可运行）
 *
 * 注意：**不要把中间文件写到 /tmp** —— OHOS 上部分目录（含 /tmp）只读，
 * 写失败会让 grep 找不到文件而误判。这里用 popen 直接读子进程输出，
 * 完全不落盘，跨平台（Windows 开发机 / OHOS CI 真机）一致。
 *
 * 用法: test_devio <devio_binary_path>
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
        printf("FAIL test_devio: missing <devio_binary> argument\n");
        return 2;
    }
    const char *devio = argv[1];

    /* ── T1: 存在 + 可执行 ── */
    expect(access(devio, F_OK) == 0, "T1 devio binary present", "(missing)");
    expect(access(devio, X_OK) == 0, "T1 devio binary executable", "(no +x)");

    /* ── T2/T3: 真实执行，读输出（不落盘） ── */
    char cmd[1024];
    snprintf(cmd, sizeof(cmd), "\"%s\" 2>&1", devio);

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        fail("T2 devio runs", "(popen failed)");
        fail("T3 output has usage keywords", "(popen failed)");
        printf("test devio 1.2: %d passed, %d failed\n", passed, failed);
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

    /* ★ 完整「跑不起来」过滤（吸收 AI 检视 P2：上一轮 T2 只判 exit_code < 126）：
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

    /* devio 无参数时打印 usage 并返回非 0（预期错误路径） */
    char detail[160];
    snprintf(detail, sizeof(detail), "(rc=%d killed=%d exit=%d bytes=%zu output=%.70s)",
             rc, killed, exit_code, n, buf);
    expect(n > 0 && !run_failed,
           "T2 devio runs and produces output (not rc==-1 / not killed / not 126-127-128+)",
           detail);

    int has_kw = strstr(buf, "Usage") || strstr(buf, "usage") ||
                 strstr(buf, "read")  || strstr(buf, "write");
    expect(has_kw, "T3 output mentions usage/read/write", detail);

    printf("test devio 1.2: %d passed, %d failed\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
