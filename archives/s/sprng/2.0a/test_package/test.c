/* test.c — sprng 2.0a 消费端冒烟测试（test_package）
 *
 * 从已安装包的角度验证 9 条断言：
 *   1  LFG 流可初始化（头文件 + 静态库链接成功）
 *   2  1000 个 double 全部落在 [0,1)
 *   3  同 seed 重初始化 ⇒ 前 16 个值逐位相同（确定性）
 *   4  同 seed 的两条独立流（gennum 0/1）首值不同（独立性）
 *   5  整数接口在 16 次调用中不是常量
 *   6  pack 得到非空缓冲
 *   7  unpack 能恢复流（非 NULL）
 *   8  恢复出的流复现相同的 16 个 double（pack/unpack 往返一致）
 *   9  第二个生成器 LCG64 与默认生成器 PMLCG(5) 都能初始化并出数
 *       —— PMLCG 会把 libsprng.a 里的 pmlcg.o 拉进链接，从而真实消费
 *          conan 传递依赖 gmp（缺依赖会在这里链接失败）
 *
 * 退出码：0 = 9/9 通过；否则 = 失败条数。
 */

#include <stdio.h>
#include <stdlib.h>

#include "sprng.h"

#define SEED 985456376

static int failures = 0;

static void check(int cond, const char *what)
{
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        failures++;
    }
}

int main(void)
{
    int *g = NULL;
    int i;
    int ok;

    /* 1. LFG 初始化 */
    g = init_sprng(SPRNG_LFG, 0, 1, SEED, 0);
    check(g != NULL, "init_sprng(SPRNG_LFG) returns a stream");

    /* 2. 数值区间 */
    if (g != NULL) {
        ok = 1;
        for (i = 0; i < 1000; i++) {
            double v = sprng(g);
            if (!(v >= 0.0 && v < 1.0))
                ok = 0;
        }
        check(ok, "1000 doubles all in [0,1)");
        free_sprng(g);
    } else {
        check(0, "1000 doubles all in [0,1)");
    }

    /* 3. 确定性：同 seed 两次初始化前 16 个值一致 */
    {
        double a[16], b[16];
        int same = 1;
        g = init_sprng(SPRNG_LFG, 0, 1, SEED, 0);
        if (g != NULL) {
            for (i = 0; i < 16; i++)
                a[i] = sprng(g);
            free_sprng(g);
        }
        g = init_sprng(SPRNG_LFG, 0, 1, SEED, 0);
        if (g != NULL) {
            for (i = 0; i < 16; i++)
                b[i] = sprng(g);
            free_sprng(g);
        } else {
            same = 0;
        }
        for (i = 0; i < 16; i++)
            if (a[i] != b[i])
                same = 0;
        check(same, "same seed reproduces the first 16 doubles");
    }

    /* 4. 独立性：同 seed 的两条流首值不同 */
    {
        int *g0, *g1;
        double v0 = -1.0, v1 = -1.0;
        g0 = init_sprng(SPRNG_LFG, 0, 2, SEED, 0);
        g1 = init_sprng(SPRNG_LFG, 1, 2, SEED, 0);
        if (g0 != NULL) {
            v0 = sprng(g0);
            free_sprng(g0);
        }
        if (g1 != NULL) {
            v1 = sprng(g1);
            free_sprng(g1);
        }
        check(g0 != NULL && g1 != NULL && v0 != v1,
              "two independent streams differ at the first value");
    }

    /* 5. 整数接口非常量 */
    {
        int first, vary = 0;
        g = init_sprng(SPRNG_LFG, 0, 1, SEED, 0);
        if (g != NULL) {
            first = isprng(g);
            for (i = 0; i < 15; i++)
                if (isprng(g) != first)
                    vary = 1;
            free_sprng(g);
        }
        check(g != NULL && vary, "integer interface is not constant over 16 draws");
    }

    /* 6-8. pack/unpack 往返（在 spawn 出的流 gennum=1 上做，与上游
     *      checksprng 的 Default 接口同一形态） */
    {
        int *gs, *gu;
        char *packed = NULL;
        int psize = 0;
        double a[16], b[16];
        int same = 1;

        gs = init_sprng(SPRNG_LFG, 1, 2, SEED, 0);
        if (gs != NULL) {
            psize = pack_sprng(gs, &packed);
            for (i = 0; i < 16; i++)
                a[i] = sprng(gs);          /* 前进原流 */
            free_sprng(gs);
        }
        check(gs != NULL && psize > 0 && packed != NULL,
              "pack_sprng returns a non-empty buffer");

        gu = (packed != NULL) ? unpack_sprng(packed) : NULL;
        check(gu != NULL, "unpack_sprng restores the stream");
        if (gu != NULL) {
            for (i = 0; i < 16; i++)
                b[i] = sprng(gu);
            free_sprng(gu);
        }
        for (i = 0; i < 16; i++)
            if (a[i] != b[i])
                same = 0;
        check(gu != NULL && same, "restored stream reproduces the same 16 doubles");
        free(packed);
    }

    /* 9. 其它生成器可用（LCG64 + PMLCG，后者真实消费 gmp 传递依赖） */
    {
        int *gl, *gp;
        int okl = 1, okp = 1;
        gl = init_sprng(SPRNG_LCG64, 0, 1, SEED, 0);
        gp = init_sprng(SPRNG_PMLCG, 0, 1, SEED, 0);
        if (gl != NULL) {
            for (i = 0; i < 100; i++) {
                double v = sprng(gl);
                if (!(v >= 0.0 && v < 1.0))
                    okl = 0;
            }
            free_sprng(gl);
        }
        if (gp != NULL) {
            for (i = 0; i < 100; i++) {
                double v = sprng(gp);
                if (!(v >= 0.0 && v < 1.0))
                    okp = 0;
            }
            free_sprng(gp);
        }
        check(gl != NULL && okl, "SPRNG_LCG64 stream yields doubles in [0,1)");
        check(gp != NULL && okp, "SPRNG_PMLCG stream works (links libgmp transitively)");
    }

    if (failures == 0)
        printf("PASS: sprng 2.0a consumer smoke 9/9\n");
    else
        printf("FAIL: sprng 2.0a consumer smoke %d/9 failed\n", failures);
    return failures;
}
