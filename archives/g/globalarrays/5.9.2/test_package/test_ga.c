/*
 * GlobalArrays 5.9.2 consumer test (OHOS, no-MPI build).
 * 真实调用 GA C API：初始化 / 创建 / Put / Get / Fill / 负向断言。
 * 不使用 assert()（Release -DNDEBUG 会移除），用 CHECK 宏。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ga.h"

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s\n", msg);                                \
            exit(1);                                                           \
        }                                                                      \
        printf("PASS: %s\n", msg);                                             \
    } while (0)

int main(int argc, char **argv)
{
    int g_a;
    int dims[2] = {4, 4};
    int lo[2] = {0, 0}, hi[2] = {3, 3};  /* C API 索引为 0-based（unit-tests ga_put.c 实证：lo=SIZE-SIZE, hi=SIZE-1） */
    int buf[16], out[16];
    int ld[1] = {4};  /* leading dimension（NGA_Put 的 capi 实现会解引用 ld，不能传 NULL） */
    int bad_dims[2] = {0, 4};
    int i;

    /* 真 MPI（mpich 依赖）下必须先 MPI_Init 再 GA_Initialize
       （shim 时代的空 MPI_Init 掩盖了这一点）。 */
    MPI_Init(&argc, &argv);
    GA_Initialize();

    /* 正负性：单进程（无 MPI）下 Nodeid/NNodes 仍可用 */
    CHECK(GA_Nodeid() >= 0, "GA_Nodeid() >= 0");

    /* 正断言：正常创建二维数组（GA handle 为负值编号，GA_OFFSET=1000，
       首个 handle 是 -1000；失败返回 0） */
    g_a = NGA_Create(C_INT, 2, dims, "test_a", NULL);
    CHECK(g_a != 0 && g_a <= -900, "NGA_Create valid array returns valid handle");

    /* 正断言：Fill + Get 往返一致 */
    for (i = 0; i < 16; i++) {
        buf[i] = i;
    }
    NGA_Put(g_a, lo, hi, buf, ld);
    NGA_Get(g_a, lo, hi, out, ld);
    CHECK(memcmp(buf, out, sizeof(buf)) == 0, "NGA_Put/NGA_Get roundtrip");

    /* 正断言：NGA_Inquire 返回维度信息 */
    {
        int ndim = -1, type = -1, qdims[2] = {0, 0};
        NGA_Inquire(g_a, &type, &ndim, qdims);
        CHECK(ndim == 2, "NGA_Inquire reports ndim == 2");
        CHECK(qdims[0] == 4 && qdims[1] == 4, "NGA_Inquire reports dims");
    }

    /* 负断言：超维数创建必须失败（capi.c 首行 if(ndim>MAXDIM) return 0，不触发 GA 错误退出） */
    {
        int big_dims[10] = {0};
        int g_bad = NGA_Create(C_INT, 10, big_dims, "bad_a", NULL);
        CHECK(g_bad == 0, "NGA_Create with ndim > MAXDIM is rejected");
    }

    GA_Destroy(g_a);
    GA_Terminate();
    MPI_Finalize();

    printf("ALL GA TESTS PASS\n");
    return 0;
}
