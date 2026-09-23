/* test.c — MUMPS 5.9.1 consumer test (double real precision)
 *
 * 通过 C 接口 dmumps_c 求解一个小型线性方程组：
 *   A = diag(1, 2), b = [1, 4]^T  →  解 x = [1, 2]^T
 * 验证库链接、初始化、分析/分解/求解、释放全链路。
 */
#include <stdio.h>
#include <math.h>
#include "dmumps_c.h"

#define JOB_INIT -1
#define JOB_END  -2
#define USE_COMM_WORLD -987654

#define ICNTL(I) icntl[(I)-1]  /* 使索引与文档一致 */

int main(void)
{
    DMUMPS_STRUC_C id;
    MUMPS_INT n = 2;
    MUMPS_INT8 nnz = 2;
    MUMPS_INT irn[2] = {1, 2};
    MUMPS_INT jcn[2] = {1, 2};
    double a[2]  = {1.0, 2.0};
    double rhs[2] = {1.0, 4.0};
    int error = 0;

    /* 初始化 MUMPS 实例（串行模式，使用 libseq 桩） */
    id.comm_fortran = USE_COMM_WORLD;
    id.par = 1;
    id.sym = 0;
    id.job = JOB_INIT;
    dmumps_c(&id);

    /* 定义问题 */
    id.n = n;
    id.nnz = nnz;
    id.irn = irn;
    id.jcn = jcn;
    id.a = a;
    id.rhs = rhs;

    /* 关闭输出 */
    id.ICNTL(1) = -1;
    id.ICNTL(2) = -1;
    id.ICNTL(3) = -1;
    id.ICNTL(4) = 0;

    /* 分析 + 分解 + 求解 */
    id.job = 6;
    dmumps_c(&id);
    if (id.infog[0] < 0) {
        printf("MUMPS error: INFOG(1)=%d INFOG(2)=%d\n", id.infog[0], id.infog[1]);
        error = 1;
    }

    /* 终止实例 */
    id.job = JOB_END;
    dmumps_c(&id);

    if (!error) {
        printf("Solution is : (%8.2f  %8.2f)\n", rhs[0], rhs[1]);
        if (fabs(rhs[0] - 1.0) > 1e-6 || fabs(rhs[1] - 2.0) > 1e-6) {
            printf("TEST FAILED: unexpected solution\n");
            return 1;
        }
        printf("TEST PASSED\n");
        return 0;
    }
    return 1;
}
