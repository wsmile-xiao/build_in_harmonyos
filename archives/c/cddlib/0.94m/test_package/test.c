/* 真实断言：用 cddlib 解一个可手算的线性不等式系统。
 * cdd.h 用到 FILE，必须**先** include <stdio.h>（否则 unknown type name 'FILE'）。 */
/* 必须先定义 GMPRATIONAL：cdd.h 据它决定数值类型。
 * 不定义则头里 mytype 退化成 double，而链接的 libcddgmp 用的是 mpq_t，
 * 二者不匹配 → 运行期内存错乱、Signal 11（实撞）。 */
#define GMPRATIONAL 1
#include <stdio.h>
#include <stdlib.h>
#include <cddlib/setoper.h>
#include <cddlib/cdd.h>

int main(void) {
    dd_set_global_constants();
    /* 半空间：x >= 0, y >= 0, -x+1 >= 0, -y+1 >= 0  →  单位正方形，应有 4 个顶点 */
    dd_MatrixPtr M = dd_CreateMatrix(4, 3);
    if (!M) { fprintf(stderr, "dd_CreateMatrix 失败\n"); return 1; }
    M->representation = dd_Inequality;
    /* 每行： b + a1*x + a2*y >= 0 */
    dd_set_si(M->matrix[0][0], 0); dd_set_si(M->matrix[0][1],  1); dd_set_si(M->matrix[0][2],  0);
    dd_set_si(M->matrix[1][0], 0); dd_set_si(M->matrix[1][1],  0); dd_set_si(M->matrix[1][2],  1);
    dd_set_si(M->matrix[2][0], 1); dd_set_si(M->matrix[2][1], -1); dd_set_si(M->matrix[2][2],  0);
    dd_set_si(M->matrix[3][0], 1); dd_set_si(M->matrix[3][1],  0); dd_set_si(M->matrix[3][2], -1);

    dd_ErrorType err = dd_NoError;
    dd_PolyhedraPtr P = dd_DDMatrix2Poly(M, &err);
    if (!P || err != dd_NoError) { fprintf(stderr, "dd_DDMatrix2Poly 失败 err=%d\n", (int)err); return 1; }
    dd_MatrixPtr G = dd_CopyGenerators(P);
    if (!G) { fprintf(stderr, "dd_CopyGenerators 失败\n"); return 1; }
    /* 单位正方形有且仅有 4 个顶点 —— 可手算 */
    if (G->rowsize != 4) { fprintf(stderr, "顶点数应为 4，实得 %ld\n", (long)G->rowsize); return 1; }
    printf("cddlib: 单位正方形顶点数=%ld 通过\n", (long)G->rowsize);
    dd_FreeMatrix(M); dd_FreeMatrix(G); dd_FreePolyhedra(P);
    dd_free_global_constants();
    return 0;
}
