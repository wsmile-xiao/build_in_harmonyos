/* mmlib 消费者 API 契约测试（链接 mmlib::mmlib，真实执行器）
 *
 * 逐用例输出 TEST PASS/FAIL，末行 TEST SUMMARY；任一失败 exit(1)。
 * 覆盖：mm_aligned_alloc/mm_aligned_free、mm_gettime/mm_relative_sleep_ms、
 * mm_thr_mutex_*、mm_setenv/mm_getenv/mm_unsetenv、mm_unlink + last-error。
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <mmlib.h>
#include <mmerrno.h>
#include <mmsysio.h>
#include <mmthread.h>
#include <mmtime.h>

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

static void test_aligned_alloc(void)
{
    int f0 = g_fails;
    printf("TEST CASE: mm_aligned_alloc / mm_aligned_free\n");
    void *p = mm_aligned_alloc(64, 1 << 20);
    CHECK(p != NULL, "mm_aligned_alloc(64, 1MiB) 返回非 NULL");
    if (p != NULL) {
        CHECK(((uintptr_t)p % 64) == 0, "返回地址按 64 字节对齐");
        memset(p, 0xAB, 1 << 20);
        const unsigned char *b = (const unsigned char *)p;
        CHECK(b[0] == 0xAB && b[(1 << 20) - 1] == 0xAB, "整块内存可读写");
        mm_aligned_free(p);
    }
    case_done("mm_aligned_alloc / mm_aligned_free", f0);
}

static void test_time(void)
{
    int f0 = g_fails;
    printf("TEST CASE: mm_gettime / mm_relative_sleep_ms\n");
    struct mm_timespec t0, t1;
    int rc0 = mm_gettime(MM_CLK_MONOTONIC, &t0);
    CHECK(rc0 == 0, "mm_gettime(MM_CLK_MONOTONIC) 第一次返回 0");
    int rc1 = mm_relative_sleep_ms(50);
    CHECK(rc1 == 0, "mm_relative_sleep_ms(50) 返回 0");
    int rc2 = mm_gettime(MM_CLK_MONOTONIC, &t1);
    CHECK(rc2 == 0, "mm_gettime(MM_CLK_MONOTONIC) 第二次返回 0");
    int64_t ms = (int64_t)(t1.tv_sec - t0.tv_sec) * 1000
                 + (int64_t)(t1.tv_nsec - t0.tv_nsec) / 1000000;
    CHECK(ms >= 40 && ms <= 2000, "单调时钟推进量 40..2000ms（50ms 睡眠）");
    case_done("mm_gettime / mm_relative_sleep_ms", f0);
}

static void test_mutex(void)
{
    int f0 = g_fails;
    printf("TEST CASE: mm_thr_mutex_*\n");
    mm_thr_mutex_t m;
    CHECK(mm_thr_mutex_init(&m, 0) == 0, "mm_thr_mutex_init 返回 0");
    int locked = mm_thr_mutex_lock(&m);
    CHECK(locked == 0, "mm_thr_mutex_lock 返回 0");
    if (locked == 0) {
        CHECK(mm_thr_mutex_trylock(&m) != 0, "已持锁时 mm_thr_mutex_trylock 返回非 0");
        CHECK(mm_thr_mutex_unlock(&m) == 0, "mm_thr_mutex_unlock 返回 0");
    }
    CHECK(mm_thr_mutex_deinit(&m) == 0, "mm_thr_mutex_deinit 返回 0");
    case_done("mm_thr_mutex_*", f0);
}

static void test_env(void)
{
    int f0 = g_fails;
    printf("TEST CASE: mm_setenv / mm_getenv / mm_unsetenv\n");
    CHECK(mm_setenv("MMLIB_TPROBE", "value123", MM_ENV_OVERWRITE) == 0,
          "mm_setenv(MM_ENV_OVERWRITE) 返回 0");
    const char *v = mm_getenv("MMLIB_TPROBE", NULL);
    CHECK(v != NULL && strcmp(v, "value123") == 0, "mm_getenv 读回写入值");
    CHECK(mm_unsetenv("MMLIB_TPROBE") == 0, "mm_unsetenv 返回 0");
    const char *v2 = mm_getenv("MMLIB_TPROBE", "fallback");
    CHECK(v2 != NULL && strcmp(v2, "fallback") == 0, "unset 后 mm_getenv 返回默认值");
    case_done("mm_setenv / mm_getenv / mm_unsetenv", f0);
}

static void test_error_state(void)
{
    int f0 = g_fails;
    printf("TEST CASE: mm_unlink / mm_get_lasterror_*\n");
    int rc = mm_unlink("/nonexistent/mmlib/consumer/probe");
    CHECK(rc != 0, "mm_unlink 不存在路径返回非 0");
    CHECK(mm_get_lasterror_number() > 0, "last-error 编号可查询（>0）");
    const char *desc = mm_get_lasterror_desc();
    CHECK(desc != NULL && desc[0] != '\0', "last-error 描述非空");
    case_done("mm_unlink / mm_get_lasterror_*", f0);
}

int main(void)
{
    printf("== mmlib consumer API contract test ==\n");
    test_aligned_alloc();
    test_time();
    test_mutex();
    test_env();
    test_error_state();
    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, g_fails == 0 ? "ALL PASS" : "FAILURES PRESENT");
    return g_fails == 0 ? 0 : 1;
}
