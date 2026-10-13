/**
 * @file test_pastix_contract.c
 *
 * @brief 消费者视角 6.4.0 契约：版本宏 / 整型位宽 / 后端开关的实际取值。
 *
 * 覆盖本包对外承诺的构建坐标（见 conanfile.py package_info 与
 * reports 契约校验）：SMP-only、静态、int32、SCOTCH 排序、hwloc 启用、
 * Fortran 包装启用、openblas 线程函数可用。
 *
 * 输出协议：逐项 CHECK PASS/FAIL、TEST SUMMARY；任一项失败 → 退出码 1。
 */
#include <stdio.h>

#include <pastix.h>
#include <pastix/config.h>
#include <spm.h>

#ifdef PASTIX_WITH_FORTRAN
#define C_FORTRAN 1
#else
#define C_FORTRAN 0
#endif

#ifdef PASTIX_WITH_MPI
#define C_MPI 1
#else
#define C_MPI 0
#endif

#ifdef PASTIX_WITH_CUDA
#define C_CUDA 1
#else
#define C_CUDA 0
#endif

#ifdef PASTIX_WITH_STARPU
#define C_STARPU 1
#else
#define C_STARPU 0
#endif

#ifdef PASTIX_WITH_PARSEC
#define C_PARSEC 1
#else
#define C_PARSEC 0
#endif

#ifdef PASTIX_INT64
#define C_INT64 1
#else
#define C_INT64 0
#endif

#ifdef HAVE_HWLOC
#define C_HWLOC 1
#else
#define C_HWLOC 0
#endif

#ifdef PASTIX_ORDERING_SCOTCH
#define C_SCOTCH 1
#else
#define C_SCOTCH 0
#endif

#ifdef PASTIX_ORDERING_METIS
#define C_METIS 1
#else
#define C_METIS 0
#endif

#ifdef PASTIX_ORDERING_PTSCOTCH
#define C_PTSCOTCH 1
#else
#define C_PTSCOTCH 0
#endif

#ifdef HAVE_OPENBLAS_SET_NUM_THREADS
#define C_OBLAS_THREADS 1
#else
#define C_OBLAS_THREADS 0
#endif

static int g_checks = 0;
static int g_fails  = 0;

#define CHECK(cond, what)                                      \
    do {                                                       \
        g_checks++;                                            \
        if (cond) {                                            \
            printf("CHECK PASS: %s\n", (what));                \
        } else {                                               \
            g_fails++;                                         \
            printf("CHECK FAIL: %s\n", (what));                \
        }                                                      \
    } while (0)

int
main(void)
{
    printf("== test_pastix_contract: PaStiX 6.4.0 构建坐标契约 ==\n");

    CHECK(PASTIX_VERSION_MAJOR == 6, "PASTIX_VERSION_MAJOR == 6");
    CHECK(PASTIX_VERSION_MINOR == 4, "PASTIX_VERSION_MINOR == 4");
    CHECK(PASTIX_VERSION_MICRO == 0, "PASTIX_VERSION_MICRO == 0");

    CHECK(C_FORTRAN == 1,        "PASTIX_WITH_FORTRAN 已启用（Fortran 包装 + 主体 Fortran 源）");
    CHECK(C_MPI == 0,            "PASTIX_WITH_MPI 未启用（SMP-only 组合面）");
    CHECK(C_CUDA == 0,           "PASTIX_WITH_CUDA 未启用");
    CHECK(C_STARPU == 0,         "PASTIX_WITH_STARPU 未启用");
    CHECK(C_PARSEC == 0,         "PASTIX_WITH_PARSEC 未启用");
    CHECK(C_INT64 == 0,          "PASTIX_INT64 未启用（int32 索引，与 scotch int32 匹配）");

    CHECK(C_HWLOC == 1,          "HAVE_HWLOC 已启用（拓扑/亲和性）");
    CHECK(C_SCOTCH == 1,         "PASTIX_ORDERING_SCOTCH 已启用");
    CHECK(C_METIS == 0,          "PASTIX_ORDERING_METIS 未启用");
    CHECK(C_PTSCOTCH == 0,       "PASTIX_ORDERING_PTSCOTCH 未启用");
    CHECK(C_OBLAS_THREADS == 1,  "HAVE_OPENBLAS_SET_NUM_THREADS 已启用（openblas 探测成功）");

    CHECK(sizeof(pastix_int_t) == 4, "sizeof(pastix_int_t) == 4");
    CHECK(sizeof(spm_int_t) == 4,    "sizeof(spm_int_t) == 4");

    printf("TEST SUMMARY: %d checks, %d failed -> %s\n",
           g_checks, g_fails, (g_fails == 0) ? "ALL PASS" : "FAILURES");
    return (g_fails == 0) ? 0 : 1;
}
