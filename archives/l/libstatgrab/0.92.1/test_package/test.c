/*
 * test_package consumer test — libstatgrab 0.92.1
 *
 * 消费者视角验证：链接 libstatgrab 库并真实调用其公开 API，
 * 断言返回值/字段有效性（R34：实质依赖被测包，禁止空壳打印）。
 */
#include <stdio.h>
#include <string.h>
#include <statgrab.h>

static int failures = 0;

#define CHECK(cond, msg)                                              \
    do {                                                              \
        if (cond) {                                                   \
            printf("PASS: %s\n", msg);                                \
        } else {                                                      \
            printf("FAIL: %s (error code: %u)\n", msg,                \
                   (unsigned int)sg_get_error());                     \
            ++failures;                                               \
        }                                                             \
    } while (0)

int main(void)
{
    size_t entries = 0;
    sg_host_info *hi = NULL;
    sg_mem_stats *ms = NULL;
    sg_load_stats *ls = NULL;
    sg_cpu_stats *cs = NULL;

    printf("== libstatgrab consumer test ==\n");

    if (sg_init(1) != SG_ERROR_NONE) {
        printf("FAIL: sg_init (error code: %u)\n",
               (unsigned int)sg_get_error());
        return 1;
    }
    CHECK(sg_get_error() == SG_ERROR_NONE, "sg_init returns SG_ERROR_NONE");

    hi = sg_get_host_info(&entries);
    CHECK(hi != NULL && entries == 1, "sg_get_host_info returns one entry");
    if (hi) {
        CHECK(hi->os_name != NULL && hi->os_name[0] != '\0',
              "host_info os_name is non-empty");
        CHECK(hi->hostname != NULL && hi->hostname[0] != '\0',
              "host_info hostname is non-empty");
    }

    ms = sg_get_mem_stats(&entries);
    CHECK(ms != NULL && entries >= 1, "sg_get_mem_stats returns entries");
    if (ms) {
        CHECK(ms->total > 0, "mem_stats total RAM > 0");
    }

    ls = sg_get_load_stats(&entries);
    CHECK(ls != NULL && entries == 1, "sg_get_load_stats returns one entry");
    if (ls) {
        CHECK(ls->min1 >= 0.0 && ls->min15 >= 0.0,
              "load_stats loads are non-negative");
    }

    cs = sg_get_cpu_stats(&entries);
    CHECK(cs != NULL && entries >= 1, "sg_get_cpu_stats returns entries");
    if (cs) {
        CHECK(cs->user > 0 || cs->kernel > 0 || cs->idle > 0,
              "cpu_stats counters are non-zero");
    }

    printf("== result: %s (%d failures) ==\n",
           failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
