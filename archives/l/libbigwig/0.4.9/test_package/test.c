#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bigWig.h"

/* 消费者冒烟测试: 写入一个小 bigWig 文件, 再读回校验 (R34: 必须调用真实 API) */
int main(void) {
    bigWigFile_t *fp = NULL;
    const char *chroms[] = {"1"};
    uint32_t chrLens[] = {1000000};
    const char *chromsUse[] = {"1", "1", "1"};
    uint32_t starts[] = {0, 100, 200};
    uint32_t ends[] = {10, 110, 210};
    float values[] = {1.5f, 2.5f, 3.5f};
    const char *out = "test_libbigwig.bw";
    int rc = 1;

    if (bwInit(1 << 17) != 0) {
        fprintf(stderr, "bwInit failed\n");
        return 1;
    }

    fp = bwOpen(out, NULL, "w");
    if (!fp) {
        fprintf(stderr, "bwOpen(w) failed\n");
        goto done;
    }
    if (bwCreateHdr(fp, 2)) goto done;
    fp->cl = bwCreateChromList(chroms, chrLens, 1);
    if (!fp->cl) goto done;
    if (bwWriteHdr(fp)) goto done;
    if (bwAddIntervals(fp, chromsUse, starts, ends, values, 3)) goto done;
    bwClose(fp);   /* bwClose 返回 void */
    fp = NULL;

    /* 读回校验 */
    fp = bwOpen(out, NULL, "r");
    if (!fp) {
        fprintf(stderr, "bwOpen(r) failed\n");
        goto done;
    }
    bwOverlappingIntervals_t *ov = bwGetOverlappingIntervals(fp, "1", 0, 300);
    if (!ov) {
        fprintf(stderr, "bwGetOverlappingIntervals failed\n");
        goto done;
    }
    if (ov->l < 3) {
        fprintf(stderr, "expected >=3 intervals, got %d\n", (int)ov->l);
        bwDestroyOverlappingIntervals(ov);
        goto done;
    }
    if (ov->value[0] != 1.5f || ov->value[1] != 2.5f || ov->value[2] != 3.5f) {
        fprintf(stderr, "value mismatch: %f %f %f\n",
                ov->value[0], ov->value[1], ov->value[2]);
        bwDestroyOverlappingIntervals(ov);
        goto done;
    }
    printf("libbigwig smoke test OK: 3 intervals read back with expected values\n");
    bwDestroyOverlappingIntervals(ov);
    rc = 0;

done:
    if (fp) bwClose(fp);
    remove(out);
    bwCleanup();
    return rc;
}
