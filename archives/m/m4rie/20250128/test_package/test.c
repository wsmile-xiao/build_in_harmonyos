/* 真实断言：m4rie 是 GF(2^e) 上的稠密矩阵库（m4ri 只做 GF(2)）。
 * 用 GF(4)=GF(2)[x]/(x²+x+1) 做单位阵乘法并逐元素比对。 */
#include <stdio.h>
#include <m4rie/m4rie.h>

int main(void) {
    /* x²+x+1 = 0b111 = 0x7，GF(4) 的不可约多项式 */
    gf2e *ff = gf2e_init(0x7);
    if (!ff) { fprintf(stderr, "gf2e_init 失败\n"); return 1; }

    mzed_t *I = mzed_init(ff, 2, 2);
    mzed_t *B = mzed_init(ff, 2, 2);
    if (!I || !B) { fprintf(stderr, "mzed_init 失败\n"); return 1; }

    /* I = 单位阵；B = [[1,2],[3,1]]（元素是 GF(4) 的位表示 0..3） */
    mzed_write_elem(I, 0, 0, 1); mzed_write_elem(I, 1, 1, 1);
    mzed_write_elem(B, 0, 0, 1); mzed_write_elem(B, 0, 1, 2);
    mzed_write_elem(B, 1, 0, 3); mzed_write_elem(B, 1, 1, 1);

    mzed_t *C = mzed_mul(NULL, I, B);   /* I·B 必须等于 B */
    if (!C) { fprintf(stderr, "mzed_mul 返回 NULL\n"); return 1; }
    for (int i = 0; i < 2; i++)
        for (int j = 0; j < 2; j++)
            if (mzed_read_elem(C, i, j) != mzed_read_elem(B, i, j)) {
                fprintf(stderr, "I*B != B 于 (%d,%d): %lu vs %lu\n", i, j,
                        (unsigned long)mzed_read_elem(C, i, j),
                        (unsigned long)mzed_read_elem(B, i, j));
                return 1;
            }
    /* 写进去的值读得回来（GF(4) 元素表示自洽） */
    if (mzed_read_elem(B, 0, 1) != 2 || mzed_read_elem(B, 1, 0) != 3) {
        fprintf(stderr, "mzed 元素读写不自洽\n"); return 1;
    }

    printf("m4rie: GF(4) 上 I*B==B 逐元素通过；元素读写自洽 通过\n");
    mzed_free(C); mzed_free(B); mzed_free(I); gf2e_free(ff);
    return 0;
}
