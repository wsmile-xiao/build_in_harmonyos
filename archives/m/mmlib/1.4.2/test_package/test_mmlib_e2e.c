/* mmlib 消费者最小应用管线（E2E，链接 mmlib::mmlib 真实执行器）
 *
 * 模拟一个真实消费方应用对 mmlib 的组合使用流（跨进程、真实数据流）：
 *   用例 1 配置流：mm_setenv 写入 → mm_getenv 读回 → mm_unsetenv 回退默认值
 *   用例 2 数据管线：mm_aligned_alloc 对齐载荷缓冲 → mm_ipc_connected_pair
 *          建连接对 → fork 生产者/消费者：父进程发送 64 项载荷，子进程
 *          接收后逐项求和并经同一管道回传，父进程核对校验和与子进程退出码
 *   用例 3 跨进程互斥：mmap 共享段 + mm_thr_mutex_init(MM_THR_PSHARED)，
 *          父子进程各持锁自增 500 次，校验最终计数（真实锁竞争流）
 *
 * 逐用例输出 TEST PASS/FAIL，末行 TEST SUMMARY；任一失败 exit(1)。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

#include <mmlib.h>
#include <mmerrno.h>
#include <mmsysio.h>
#include <mmthread.h>
#include <mmtime.h>

#define ITEMS 64
#define PAYLOAD_BYTES (ITEMS * (int)sizeof(int64_t))
#define ROUNDS 500

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, what)                                                      \
    do {                                                                       \
        g_checks++;                                                            \
        if (cond) {                                                            \
            printf("  CHECK PASS: %s\n", (what));                              \
        } else {                                                               \
            printf("  CHECK FAIL: %s (%s:%d)\n", (what), __FILE__, __LINE__);  \
            g_fails++;                                                         \
        }                                                                      \
    } while (0)

static void case_done(const char *name, int fails_before)
{
    if (g_fails == fails_before) {
        printf("TEST PASS: %s\n", name);
    } else {
        printf("TEST FAIL: %s\n", name);
    }
}

static int64_t sum_payload(const int64_t *v, int n)
{
    int64_t s = 0;
    int i;
    for (i = 0; i < n; i++)
        s += v[i];
    return s;
}

/* ---- 用例 1：配置流 -------------------------------------------------- */

static void test_config_flow(void)
{
    int f0 = g_fails;
    printf("TEST CASE: 配置流（mm_setenv / mm_getenv / mm_unsetenv）\n");
    CHECK(mm_setenv("MMLIB_E2E_MODE", "pipeline", MM_ENV_OVERWRITE) == 0,
          "mm_setenv(MMLIB_E2E_MODE=pipeline) 返回 0");
    const char *v = mm_getenv("MMLIB_E2E_MODE", NULL);
    CHECK(v != NULL && strcmp(v, "pipeline") == 0,
          "mm_getenv 读回管线配置值");
    CHECK(mm_unsetenv("MMLIB_E2E_MODE") == 0, "mm_unsetenv 返回 0");
    v = mm_getenv("MMLIB_E2E_MODE", "fallback");
    CHECK(v != NULL && strcmp(v, "fallback") == 0,
          "清理后 mm_getenv 回退默认值");
    case_done("配置流（mm_setenv / mm_getenv / mm_unsetenv）", f0);
}

/* ---- 用例 2：生产者/消费者数据管线 ----------------------------------- */

static void child_pipeline(int fd)
{
    int64_t buf[ITEMS];
    int64_t sum;
    ssize_t rv, wv;

    rv = mm_read(fd, buf, PAYLOAD_BYTES);
    if (rv != (ssize_t)PAYLOAD_BYTES) {
        fprintf(stderr, "E2E child: mm_read rv=%zd lasterr=%d\n",
                rv, mm_get_lasterror_number());
        _exit(2);
    }
    sum = sum_payload(buf, ITEMS);
    wv = mm_write(fd, &sum, sizeof(sum));
    if (wv != (ssize_t)sizeof(sum)) {
        fprintf(stderr, "E2E child: mm_write rv=%zd lasterr=%d\n",
                wv, mm_get_lasterror_number());
        _exit(3);
    }
    _exit(0);
}

static void test_data_pipeline(void)
{
    int f0 = g_fails, i, ws = 0;
    int fds[2];
    int64_t *in;
    ssize_t wv, rv;
    int64_t got = 0;
    pid_t pid;

    printf("TEST CASE: IPC 数据管线（对齐载荷 + fork 生产者/消费者）\n");

    CHECK(mm_ipc_connected_pair(fds) == 0,
          "mm_ipc_connected_pair 建立进程间连接对");

    in = mm_aligned_alloc(64, PAYLOAD_BYTES);
    CHECK(in != NULL && (((uintptr_t)in % 64) == 0),
          "mm_aligned_alloc 产出 64 字节对齐载荷缓冲");
    if (in == NULL) {
        case_done("IPC 数据管线（对齐载荷 + fork 生产者/消费者）", f0);
        return;
    }
    for (i = 0; i < ITEMS; i++)
        in[i] = (int64_t)i * 3 + 11;

    pid = fork();
    CHECK(pid >= 0, "fork 生产者/消费者子进程");
    if (pid == 0) {
        mm_close(fds[0]);
        child_pipeline(fds[1]); /* 不返回 */
    }
    mm_close(fds[1]);

    wv = mm_write(fds[0], in, PAYLOAD_BYTES);
    CHECK(wv == (ssize_t)PAYLOAD_BYTES, "父进程整块发送 64 项载荷（512 字节）");

    rv = mm_read(fds[0], &got, sizeof(got));
    CHECK(rv == (ssize_t)sizeof(got), "父进程收到子进程回传校验和");
    CHECK(got == sum_payload(in, ITEMS), "回传校验和与发送端逐项求和一致");

    waitpid(pid, &ws, 0);
    CHECK(WIFEXITED(ws) && WEXITSTATUS(ws) == 0, "子进程管线阶段退出码 0");

    mm_close(fds[0]);
    mm_aligned_free(in);
    case_done("IPC 数据管线（对齐载荷 + fork 生产者/消费者）", f0);
}

/* ---- 用例 3：跨进程共享互斥 ------------------------------------------ */

static void test_pshared_mutex(void)
{
    int f0 = g_fails, i, ws = 0;
    struct shared {
        mm_thr_mutex_t lock;
        int64_t counter;
    } *sh;
    pid_t pid;

    printf("TEST CASE: 跨进程互斥（mmap 共享段 + MM_THR_PSHARED）\n");

    sh = mmap(NULL, 4096, PROT_READ | PROT_WRITE,
              MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    CHECK(sh != MAP_FAILED, "mmap(MAP_SHARED|MAP_ANONYMOUS) 成功");
    if (sh == MAP_FAILED) {
        case_done("跨进程互斥（mmap 共享段 + MM_THR_PSHARED）", f0);
        return;
    }
    sh->counter = 0;
    CHECK(mm_thr_mutex_init(&sh->lock, MM_THR_PSHARED) == 0,
          "mm_thr_mutex_init(MM_THR_PSHARED) 返回 0");

    pid = fork();
    CHECK(pid >= 0, "fork 竞争子进程");
    if (pid == 0) {
        for (i = 0; i < ROUNDS; i++) {
            mm_thr_mutex_lock(&sh->lock);
            sh->counter++;
            mm_thr_mutex_unlock(&sh->lock);
        }
        _exit(0);
    }

    for (i = 0; i < ROUNDS; i++) {
        mm_thr_mutex_lock(&sh->lock);
        sh->counter++;
        mm_thr_mutex_unlock(&sh->lock);
    }

    waitpid(pid, &ws, 0);
    CHECK(WIFEXITED(ws), "子进程正常退出（锁竞争无死锁）");
    CHECK(sh->counter == 2 * ROUNDS,
          "跨进程计数 = 1000（进程共享互斥语义正确）");

    mm_thr_mutex_deinit(&sh->lock);
    munmap(sh, 4096);
    case_done("跨进程互斥（mmap 共享段 + MM_THR_PSHARED）", f0);
}

int main(void)
{
    alarm(60); /* 真机负载波动防挂死：超时即杀，判定为失败而非永久阻塞 */
    printf("== mmlib consumer E2E pipeline ==\n");
    test_config_flow();
    test_data_pipeline();
    test_pshared_mutex();
    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, g_fails == 0 ? "ALL PASS" : "FAILURES PRESENT");
    return g_fails == 0 ? 0 : 1;
}
