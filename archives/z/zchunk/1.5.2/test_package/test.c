/* test_package consumer test for zchunk 1.5.2
 * 以库使用者身份真实调用 libzck 公开 API：zck_init_write 创建 zstd 压缩流、
 * zck_write 写入、zck_close 落盘；再 zck_init_read 解析头部，校验分块数、
 * 分块大小、分块有效性与压缩是否真实生效（压缩后尺寸 < 原始尺寸）。
 * API 调用顺序与上游工具 src/zck.c、src/zck_read_header.c 一致。 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <zck.h>

static char payload[] =
    "zchunk consumer test payload 0123456789 "
    "zchunk consumer test payload ABCDEFGHIJ "
    "zchunk consumer test payload abcdefghij";

int main(void) {
    /* E002: OHOS 设备 /tmp 不可写——优先 TMPDIR，退回当前目录 */
    const char *td = getenv("TMPDIR");
    char tmpl[256];
    if (!td || access(td, W_OK) != 0)
        td = ".";
    snprintf(tmpl, sizeof(tmpl), "%s/zck_consumer_XXXXXX", td);
    int fd = mkstemp(tmpl);
    if (fd < 0) {
        perror("mkstemp");
        return 1;
    }

    /* 写入端：与上游 src/zck.c 一致 create → init_write → write → close */
    zckCtx *w = zck_create();
    if (!w) {
        fprintf(stderr, "FAIL: zck_create returned NULL\n");
        return 1;
    }
    if (!zck_init_write(w, fd)) {
        fprintf(stderr, "FAIL: zck_init_write\n");
        return 1;
    }
    size_t plen = sizeof(payload) - 1;
    if (zck_write(w, payload, plen) != (ssize_t)plen) {
        fprintf(stderr, "FAIL: zck_write\n");
        return 1;
    }
    if (!zck_close(w)) {
        fprintf(stderr, "FAIL: zck_close\n");
        return 1;
    }
    zck_free(&w);
    if (w != NULL) {
        fprintf(stderr, "FAIL: zck_free did not NULL the context\n");
        return 1;
    }

    /* 读取端：与上游 src/zck_read_header.c 一致 create → init_read */
    int rfd = open(tmpl, O_RDONLY);
    if (rfd < 0) {
        perror("open for read");
        return 1;
    }
    zckCtx *r = zck_create();
    if (!r) {
        fprintf(stderr, "FAIL: zck_create (reader)\n");
        return 1;
    }
    if (!zck_init_read(r, rfd)) {
        fprintf(stderr, "FAIL: zck_init_read\n");
        return 1;
    }
    ssize_t count = zck_get_chunk_count(r);
    if (count < 1) {
        fprintf(stderr, "FAIL: chunk count %zd < 1\n", count);
        return 1;
    }
    /* zchunk 自动分块（buzhash）会产生空的首 chunk（length=0，与上游
     * read_single_chunk.c 直接读 chunk 1 一致），找第一个非空 chunk 断言 */
    zckChunk *first = NULL;
    for (ssize_t i = 0; i < count; i++) {
        zckChunk *c = zck_get_chunk(r, (size_t)i);
        if (c && zck_get_chunk_size(c) > 0) {
            first = c;
            break;
        }
    }
    if (!first) {
        fprintf(stderr, "FAIL: no non-empty chunk in %zd\n", count);
        return 1;
    }
    ssize_t csize = zck_get_chunk_size(first);
    if (csize != (ssize_t)plen) {
        fprintf(stderr, "FAIL: chunk size %zd != payload %zu\n", csize, plen);
        return 1;
    }
    /* 回读 chunk 数据做 round-trip 校验（valid 标志在读取校验时置位，
     * 必须先经 zck_get_chunk_data 触发哈希验证） */
    char *buf = malloc((size_t)csize);
    if (!buf) {
        fprintf(stderr, "FAIL: malloc\n");
        return 1;
    }
    ssize_t got = zck_get_chunk_data(first, buf, (size_t)csize);
    if (got != csize || memcmp(buf, payload, (size_t)csize) != 0) {
        fprintf(stderr, "FAIL: chunk data round-trip mismatch (got %zd)\n",
                got);
        return 1;
    }
    free(buf);
    if (zck_get_chunk_valid(first) != 1) {
        fprintf(stderr, "FAIL: first chunk not valid\n");
        return 1;
    }
    /* 压缩生效断言：zstd 压缩后尺寸必须小于原始尺寸 */
    ssize_t comp_size = zck_get_chunk_comp_size(first);
    if (comp_size >= csize) {
        fprintf(stderr, "FAIL: comp size %zd >= raw %zd (zstd not engaged?)\n",
                comp_size, csize);
        return 1;
    }
    char *dg = zck_get_chunk_digest(first);
    if (!dg || strlen(dg) == 0) {
        fprintf(stderr, "FAIL: empty chunk digest\n");
        return 1;
    }
    printf("zchunk consumer test OK: chunks=%zd raw=%zd comp=%zd digest=%s\n",
           count, csize, comp_size, dg);
    free(dg);

    zck_free(&r);
    close(rfd);
    close(fd);
    unlink(tmpl);
    return 0;
}
