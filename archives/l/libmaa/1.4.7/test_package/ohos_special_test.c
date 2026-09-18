#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <sys/time.h>
#include "maa.h"

/* 鸿蒙专项测试（OHOS special test）
 *
 * 覆盖本次 libmaa 1.4.7 适配在 HarmonyOS PC (aarch64, OHOS/armv8) 上的两个平台适配点，
 * 均通过公开 API 验证，使用真实编译产物运行：
 *
 * 1. timer (tim_*)：timer.c 依赖 <sys/resource.h> 的 getrusage()。旧适配笔记曾因
 *    "musl 缺 sys/resource.h" 排除 timer.c；本适配以 HAVE_HEADER_SYS_RESOURCE_H=1
 *    恢复全量编译。本用例实际调用 tim_start/tim_stop/tim_get_* 验证 getrusage
 *    在 OHOS 上真实返回 CPU 时间（而非全 0）。
 *    注意：上游 timer.c 的 DIFFTIME 宏对 tv_usec 做整数除法（`(now-then).tv_usec/1000000`），
 *    亚秒精度会被截断为 0，这是上游固有行为、与平台无关；因此本用例自旋 ≥1.1s
 *    以跨过整数秒边界，确保 gettimeofday 与 getrusage 两条路径都产生可观测非零值。
 *
 * 2. bit (bit_*)：bit_* API 操作单个 unsigned long（0..63 位）。bit_cnt() 在
 *    SIZEOF_LONG==8 时走 64 位 popcount 分支。本用例置位 0 与 63（最高位），
 *    验证 SIZEOF_LONG=8 分支被正确编译执行（若误为 4，63 位会越界且计数错误）。
 */

int main(void) {
    int rc = 0;

    maa_init("libmaa-ohos-special-test");

    /* ---- 1) timer / getrusage（OHOS 平台恢复验证） ---- */
    tim_start("ohos_timer_probe");
    {
        /* 自旋 ≥1.1s 墙钟时间（见文件头 DIFFTIME 说明），全部占用 CPU */
        struct timeval tv0, tv1;
        gettimeofday(&tv0, NULL);
        volatile double acc = 0.0;
        do {
            for (int i = 0; i < 100000; i++) {
                acc += (double)i * 1e-9;
            }
            gettimeofday(&tv1, NULL);
        } while ((tv1.tv_sec - tv0.tv_sec) * 1000000L
                 + (tv1.tv_usec - tv0.tv_usec) < 1100000L);
        (void)acc;
    }
    tim_stop("ohos_timer_probe");

    double real = tim_get_real("ohos_timer_probe");
    double user = tim_get_user("ohos_timer_probe");
    double sys  = tim_get_system("ohos_timer_probe");
    printf("tim: real=%.6f user=%.6f sys=%.6f\n", real, user, sys);
    if (!(isfinite(real) && real >= 0.0)) {
        fprintf(stderr, "FAIL: tim_get_real invalid (gettimeofday path broken)\n");
        rc = 1;
    }
    if (real < 1.0) {
        fprintf(stderr, "FAIL: tim_get_real %.1f < 1.0 after 1.1s spin\n", real);
        rc = 1;
    }
    /* 1.1s 纯 CPU 自旋：若 getrusage 可用，user+sys 必 ≥1.0（整数秒截断）；
     * 若 OHOS 上 getrusage 实际不可用（历史笔记假设），将全 0。 */
    if (!(isfinite(user) && isfinite(sys))) {
        fprintf(stderr, "FAIL: tim_get_user/system non-finite\n");
        rc = 1;
    } else if (user + sys < 1.0) {
        fprintf(stderr, "FAIL: getrusage returns zero CPU time on OHOS "
                        "(user=%.2f sys=%.2f)\n", user, sys);
        rc = 1;
    }
    tim_reset("ohos_timer_probe");

    /* ---- 2) bit / SIZEOF_LONG=8（aarch64 位宽验证，单 unsigned long） ---- */
    unsigned long bits = 0UL;
    bit_set(&bits, 0);
    bit_set(&bits, 31);
    bit_set(&bits, 63);   /* 64 位 long 的最高位 */
    /* 注意：bit_tst 返回 int，掩码 0x8000000000000000（第 63 位）截断为 int 后为 0，
     * 属上游固有行为（与平台无关），故 bit_tst 只断言 0..31 位；第 63 位由
     * bit_cnt（64 位 popcount 分支）验证：若 SIZEOF_LONG 误为 4，计数将错误。 */
    if (!(bit_tst(&bits, 0) && bit_tst(&bits, 31))) {
        fprintf(stderr, "FAIL: bit_tst after bit_set\n");
        rc = 1;
    }
    if (bit_tst(&bits, 1) || bit_tst(&bits, 30)) {
        fprintf(stderr, "FAIL: bit_tst false positive\n");
        rc = 1;
    }
    int cnt = bit_cnt(&bits);
    printf("bit: cnt=%d (expect 3)\n", cnt);
    if (cnt != 3) {
        fprintf(stderr, "FAIL: bit_cnt = %d, expected 3 (SIZEOF_LONG branch wrong?)\n", cnt);
        rc = 1;
    }
    bit_clr(&bits, 63);
    cnt = bit_cnt(&bits);
    if (cnt != 2) {
        fprintf(stderr, "FAIL: bit_cnt after clr = %d, expected 2\n", cnt);
        rc = 1;
    }
    printf("bit: after clr cnt=%d\n", cnt);

    /* ---- 3) maa_version 一致性（本平台编译产物版本宏） ---- */
    printf("version: %s (%d.%d.%d)\n", maa_version(),
           maa_version_major(), maa_version_minor(), maa_version_teeny());

    maa_shutdown();
    if (rc == 0) {
        printf("libmaa OHOS special test: PASS\n");
    }
    return rc;
}