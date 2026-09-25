#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <cgranges.h>

/* 消费者测试: 通过公开头文件 cgranges.h 调用 cgranges API，
 * 验证打包产物（libcgranges.a + 头文件）可编译、链接并正确运行。
 * 注意: Release 构建定义 NDEBUG，故所有检查用显式错误处理，
 * 不依赖 assert()（避免初始化调用被剥离）。 */
static int g_fail = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); g_fail = 1; } \
    else { printf("PASS: %s\n", msg); } \
} while (0)

int main(void) {
    cgranges_t *cr = cr_init();
    CHECK(cr != NULL, "cr_init");
    if (cr == NULL) return 1;

    if (cr_add_ctg(cr, "chr1", 1000000) != 0) { fprintf(stderr, "FAIL: cr_add_ctg chr1\n"); g_fail = 1; }
    if (cr_add(cr, "chr1", 100, 200, 1) == NULL) { fprintf(stderr, "FAIL: cr_add 1\n"); g_fail = 1; }
    if (cr_add(cr, "chr1", 150, 250, 2) == NULL) { fprintf(stderr, "FAIL: cr_add 2\n"); g_fail = 1; }
    if (cr_add(cr, "chr1", 1000, 2000, 3) == NULL) { fprintf(stderr, "FAIL: cr_add 3\n"); g_fail = 1; }
    cr_index(cr);

    int64_t m = 0, n = 0;
    int64_t *b = NULL;
    n = cr_overlap(cr, "chr1", 140, 160, &b, &m);
    CHECK(n == 2, "cr_overlap [140,160) 命中 2 个区间");
    free(b); b = NULL; m = 0;

    n = cr_contain(cr, "chr1", 0, 300, &b, &m);
    CHECK(n == 2, "cr_contain [0,300) 包含 2 个区间");
    free(b); b = NULL; m = 0;

    n = cr_overlap(cr, "chr2", 0, 1000, &b, &m);
    CHECK(n == 0, "cr_overlap chr2 (无区间) 命中 0");
    free(b);

    cr_destroy(cr);
    printf(g_fail ? "cgranges consumer test: FAIL\n" : "cgranges consumer test: PASS (cr_init/add/index/overlap/contain)\n");
    return g_fail ? 1 : 0;
}