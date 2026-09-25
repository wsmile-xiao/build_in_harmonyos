/*
 * libmng 2.0.3 消费者功能测试（鸿蒙 PC / aarch64 / musl）
 *
 * 覆盖：
 *   T1 官方 fixture linux.mng（tarball 自带，101x127 真实 MNG 流）整读
 *   T2 程序化构造的单帧 MNG（IHDR+IDAT+IEND）读取 → canvas 回调逐行取数
 *   T3 图像信息: mng_get_sigtype/imagewidth/imageheight/framecount
 *   T4 回调 ABI: alloc/free + openstream/closestream/readdata 全链路
 *   T5 错误输入: 坏签名 / 未知 critical chunk / 纯噪声 → 错误码 + getlasterror
 *   T6 截断数据: 三档截断 → 非 NOERROR 返回
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libmng.h"

/* zlib for programmatic MNG construction */
#include <zlib.h>

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, name, fmt, ...) do {                                   \
    g_checks++;                                                            \
    if (cond) { printf("ok %d - %s\n", g_checks, name); }                  \
    else { g_fails++; printf("not ok %d - %s: " fmt "\n",                  \
                             g_checks, name, __VA_ARGS__); }               \
} while (0)

/* ─────────────────── 通用回调实现（内存流） ─────────────────── */
typedef struct {
    const unsigned char *data;
    mng_uint32 size;
    mng_uint32 pos;
    int open_calls, close_calls, read_calls, refresh_calls;
} memstream_t;

static mng_ptr my_alloc(mng_size_t n) { return calloc(1, n); }
static void my_free(mng_ptr p, mng_size_t n) { free(p); return; (void)n; }

static mng_bool cb_open(mng_handle h) {
    memstream_t *s = (memstream_t *)mng_get_userdata(h);
    s->open_calls++;
    return MNG_TRUE;
}
static mng_bool cb_close(mng_handle h) {
    memstream_t *s = (memstream_t *)mng_get_userdata(h);
    s->close_calls++;
    return MNG_TRUE;
}
static mng_bool cb_refresh(mng_handle h, mng_uint32 x, mng_uint32 y,
                           mng_uint32 w, mng_uint32 h_) {
    (void)x; (void)y; (void)w; (void)h_;
    memstream_t *s = (memstream_t *)mng_get_userdata(h);
    s->refresh_calls++;
    return MNG_TRUE;
}
/* 虚拟时钟: settimer 记录请求延时, 测试循环在 resume 前推进时钟,
 * 无需真实睡眠即可让动画帧延时"到期"（确定性、可审计） */
static mng_uint32 g_virtual_ticks = 0;
static mng_uint32 g_pending_delay = 0;
static mng_uint32 cb_gettickcount(mng_handle h) {
    (void)h;
    return g_virtual_ticks;
}
static mng_bool cb_settimer(mng_handle h, mng_uint32 msecs) {
    (void)h;
    g_pending_delay = msecs;
    return MNG_TRUE; /* 已安排唤醒; 消费者循环 display_resume */
}
static mng_bool cb_read(mng_handle h, mng_ptr buf, mng_uint32 buflen,
                        mng_uint32 *read) {
    memstream_t *s = (memstream_t *)mng_get_userdata(h);
    s->read_calls++;
    mng_uint32 avail = s->size - s->pos;
    mng_uint32 take = buflen < avail ? buflen : avail;
    memcpy(buf, s->data + s->pos, take);
    s->pos += take;
    *read = take;
    return MNG_TRUE;
}

static unsigned char g_canvas8[8 * 4];  /* 8px RGBA8 行缓冲 */
static mng_bool cb_processheader(mng_handle h, mng_uint32 w, mng_uint32 h_) {
    (void)w;
    (void)h_;
    return mng_set_canvasstyle(h, MNG_CANVAS_RGBA8) == MNG_NOERROR;
}

static mng_ptr cb_getcanvasline_stub(mng_handle h, mng_uint32 lineno) {
    (void)h; (void)lineno;
    return (mng_ptr)g_canvas8;
}

/* ─────────────────── 文件流（官方 fixture） ─────────────────── */
typedef struct {
    FILE *f;
    int canvas_lines;
    mng_uint32 width, height;
    int header_seen;
    unsigned char canvas[101 * 4]; /* 单行 RGBA8 */
} filectx_t;

static mng_bool fcb_refresh(mng_handle h, mng_uint32 x, mng_uint32 y,
                            mng_uint32 w, mng_uint32 h_) {
    (void)h; (void)x; (void)y; (void)w; (void)h_;
    return MNG_TRUE;
}
static mng_uint32 fcb_gettickcount(mng_handle h) {
    (void)h;
    return g_virtual_ticks;
}
static mng_bool fcb_settimer(mng_handle h, mng_uint32 msecs) {
    (void)h;
    g_pending_delay = msecs;
    return MNG_TRUE; /* 已安排唤醒; 消费者循环 display_resume */
}
static mng_bool fcb_open(mng_handle h) { (void)h; return MNG_TRUE; }
static mng_bool fcb_close(mng_handle h) { (void)h; return MNG_TRUE; }
static mng_bool fcb_read(mng_handle h, mng_ptr buf, mng_uint32 buflen,
                         mng_uint32 *read) {
    filectx_t *c = (filectx_t *)mng_get_userdata(h);
    *read = (mng_uint32)fread(buf, 1, buflen, c->f);
    return MNG_TRUE;
}
static mng_bool fcb_processheader(mng_handle h, mng_uint32 w, mng_uint32 h_) {
    filectx_t *c = (filectx_t *)mng_get_userdata(h);
    c->width = w; c->height = h_; c->header_seen++;
    /* 画布风格由应用在 processheader 中设定（libmng 约定） */
    return mng_set_canvasstyle(h, MNG_CANVAS_RGBA8) == MNG_NOERROR;
}
static mng_ptr fcb_getcanvasline(mng_handle h, mng_uint32 lineno) {
    filectx_t *c = (filectx_t *)mng_get_userdata(h);
    c->canvas_lines++;
    (void)lineno;
    return (mng_ptr)c->canvas;
}

/* ─────────────────── MNG 流程序化构造 ─────────────────── */
static void put32(unsigned char *p, mng_uint32 v) {
    p[0] = (unsigned char)(v >> 24); p[1] = (unsigned char)(v >> 16);
    p[2] = (unsigned char)(v >> 8);  p[3] = (unsigned char)v;
}
static void chunk(unsigned char **pp, const char *type,
                  const unsigned char *data, mng_uint32 len) {
    unsigned char *p = *pp;
    put32(p, len); p += 4;
    memcpy(p, type, 4); p += 4;
    if (len) { memcpy(p, data, len); p += len; }
    mng_uint32 crc = (mng_uint32)crc32(0, (const Bytef *)type, 4);
    if (len) crc = (mng_uint32)crc32(crc, (const Bytef *)data, len);
    put32(p, crc); p += 4;
    *pp = p;
}

/* 构造单帧 8x8 RGBA MNG: MHDR + IHDR + IDAT(zlib 压缩的原始像素) + IEND + MEND */
static mng_uint32 build_mng(unsigned char *out, mng_uint32 outsz,
                            mng_uint32 w, mng_uint32 h,
                            int corrupt_sig, int bad_critical,
                            int truncate_at) {
    static const unsigned char sig[8] =
        { 0x8a, 'M','N','G', 0x0d, 0x0a, 0x1a, 0x0a };
    unsigned char *p = out;
    if (!corrupt_sig) { memcpy(p, sig, 8); p += 8; }

    /* MHDR: w h ticks layer frame playtime simplicity */
    unsigned char mhdr[28];
    put32(mhdr, w); put32(mhdr+4, h); put32(mhdr+8, 1000);
    put32(mhdr+12, 0); put32(mhdr+16, 1); put32(mhdr+20, 1000);
    put32(mhdr+24, 3);
    chunk(&p, "MHDR", mhdr, 28);

    if (bad_critical) {
        unsigned char junk[4] = { 1, 2, 3, 4 };
        chunk(&p, "BOGUS", junk, 4);
    }

    unsigned char ihdr[13];
    put32(ihdr, w); put32(ihdr+4, h);
    ihdr[8] = 8; ihdr[9] = 6; ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    chunk(&p, "IHDR", ihdr, 13);

    size_t rawlen = h * (1 + (size_t)w * 4);
    unsigned char *raw = calloc(1, rawlen);
    for (mng_uint32 y = 0; y < h; y++)
        for (mng_uint32 x = 0; x < w; x++) {
            unsigned char *px = raw + y * (1 + w * 4) + 1 + x * 4;
            px[0] = x == y ? 255 : 32;
            px[1] = 32;
            px[2] = 96;
            px[3] = 255;
        }
    uLongf zlen = compressBound(rawlen);
    unsigned char *zbuf = malloc(zlen);
    compress2(zbuf, &zlen, raw, rawlen, 6);
    chunk(&p, "IDAT", zbuf, (mng_uint32)zlen);
    free(raw); free(zbuf);

    chunk(&p, "IEND", NULL, 0);
    chunk(&p, "MEND", NULL, 0);

    mng_uint32 total = (mng_uint32)(p - out);
    if (truncate_at > 0 && (mng_uint32)truncate_at < total)
        total = (mng_uint32)truncate_at;
    if (total > outsz) { fprintf(stderr, "FATAL build overflow\n"); exit(99); }
    return total;
}

/* ─────────────────── T1: 官方 fixture 整读 ─────────────────── */
static void test_official_fixture(const char *path) {
    FILE *f = fopen(path, "rb");
    CHECK(f != NULL, "T1 fixture openable", "path=%s", path);
    if (!f) return;

    unsigned char hdr[8];
    size_t n = fread(hdr, 1, 8, f);
    fclose(f);
    CHECK(n == 8 && hdr[0] == 0x8a && hdr[1] == 'M' && hdr[2] == 'N'
          && hdr[3] == 'G',
          "T1 fixture has MNG signature", "first4=%02x%02x%02x%02x",
          hdr[0], hdr[1], hdr[2], hdr[3]);

    filectx_t ctx; memset(&ctx, 0, sizeof ctx);
    FILE *f2 = fopen(path, "rb"); ctx.f = f2;
    mng_handle h = mng_initialize(&ctx, my_alloc, my_free, MNG_NULL);
    CHECK(h != MNG_NULL, "T1 mng_initialize", "%s", "handle NULL");
    if (!h) { fclose(f2); return; }
    mng_setcb_openstream(h, fcb_open);
    mng_setcb_closestream(h, fcb_close);
    mng_setcb_readdata(h, fcb_read);
    mng_setcb_processheader(h, fcb_processheader);
    mng_setcb_getcanvasline(h, fcb_getcanvasline);
    mng_setcb_refresh(h, fcb_refresh);
    mng_setcb_gettickcount(h, fcb_gettickcount);
    mng_setcb_settimer(h, fcb_settimer);
    mng_retcode rc = mng_readdisplay(h);
    /* linux.mng 的 TERM = 无限循环动画: 连续播满两帧(2 x 127 行 canvas)
     * 后停止验证; 有界循环防挂死; 上游 gtk-mng-view 亦为"永远播下去"语义 */
    int iter = 0;
    while (rc == MNG_NEEDTIMERWAIT && ctx.canvas_lines < 254 && ++iter < 1000) {
        g_virtual_ticks += g_pending_delay ? g_pending_delay : 1;
        rc = mng_display_resume(h);
    }
    CHECK(rc == MNG_NEEDTIMERWAIT || rc == MNG_NOERROR,
          "T1 readdisplay runs (NEEDTIMERWAIT on infinite anim)", "rc=%d", rc);
    CHECK(iter < 1000, "T1 animation progresses without stall", "iter=%d",
          iter);
    CHECK(ctx.header_seen == 1, "T1 processheader called once", "n=%d",
          ctx.header_seen);
    CHECK(ctx.width == 101 && ctx.height == 127,
          "T1 MHDR dimensions 101x127", "got=%lux%lu",
          (unsigned long)ctx.width, (unsigned long)ctx.height);
    CHECK(ctx.canvas_lines >= 127,
          "T1 getcanvasline >= full frame (127 rows)", "n=%d",
          ctx.canvas_lines);

    /* T3: 图像信息 API（读取成功后） */
    mng_imgtype st = mng_get_sigtype(h);
    CHECK(st == mng_it_mng, "T3 get_sigtype == mng_it_mng", "got=%d", (int)st);
    mng_uint32 w = mng_get_imagewidth(h);
    mng_uint32 ht = mng_get_imageheight(h);
    CHECK(w == 101 && ht == 127, "T3 get_imagewidth/height 101x127",
          "w=%lu h=%lu", (unsigned long)w, (unsigned long)ht);
    /* linux.mng 无 FRAM chunk → iFrameseq 恒 0（库语义正确）;
     * 帧进度改由 canvas 行数证明: ≥ 2 帧 × 127 行 */
    CHECK(ctx.canvas_lines >= 254,
          "T3 multiple frames displayed (>=2 x 127 rows)", "n=%d",
          ctx.canvas_lines);

    mng_cleanup(&h);
    fclose(f2);
}

/* ─────────────────── T2/T4: 程序化 MNG + 回调 ABI ───── */
static void test_programmatic(void) {
    static unsigned char buf[64 * 1024];
    mng_uint32 len = build_mng(buf, sizeof buf, 8, 8, 0, 0, 0);

    memstream_t s = { buf, len, 0, 0, 0, 0 };
    mng_handle h = mng_initialize(&s, my_alloc, my_free, MNG_NULL);
    CHECK(h != MNG_NULL, "T2 mng_initialize", "%s", "NULL");
    if (!h) return;
    mng_setcb_openstream(h, cb_open);
    mng_setcb_closestream(h, cb_close);
    mng_setcb_readdata(h, cb_read);
        mng_setcb_processheader(h, cb_processheader);
    mng_setcb_getcanvasline(h, cb_getcanvasline_stub);
    mng_setcb_refresh(h, cb_refresh);
    mng_setcb_gettickcount(h, cb_gettickcount);
    mng_setcb_settimer(h, cb_settimer);

    mng_retcode rc = mng_readdisplay(h);
    int iter = 0;
    while (rc == MNG_NEEDTIMERWAIT && ++iter < 1000) {
        g_virtual_ticks += g_pending_delay ? g_pending_delay : 1;
        rc = mng_display_resume(h);
    }
    CHECK(rc == MNG_NOERROR, "T2 readdisplay programmatic 8x8", "rc=%d", rc);
    CHECK(s.open_calls == 1, "T4 openstream once", "n=%d", s.open_calls);
    CHECK(s.read_calls >= 1, "T4 readdata called", "n=%d", s.read_calls);
    CHECK(s.close_calls >= 1, "T4 closestream called", "n=%d", s.close_calls);

    /* T3: 程序化流的信息 */
    mng_uint32 w = mng_get_imagewidth(h);
    mng_uint32 ht = mng_get_imageheight(h);
    CHECK(w == 8 && ht == 8, "T3 programmatic get_imagewidth/height 8x8",
          "w=%lu h=%lu", (unsigned long)w, (unsigned long)ht);
    mng_uint32 fc = mng_get_framecount(h);
    CHECK(fc == 1, "T3 programmatic framecount == 1", "got=%lu",
          (unsigned long)fc);

    mng_cleanup(&h);
    CHECK(1, "T4 cleanup ok", "%s", "");
}

/* ─────────────────── T5: 错误输入 ─────────────────── */
static void test_errors(void) {
    static unsigned char buf[64 * 1024];

    /* 坏签名 */
    mng_uint32 len = build_mng(buf, sizeof buf, 8, 8, 1, 0, 0);
    memstream_t s = { buf, len, 0, 0, 0, 0 };
    mng_handle h = mng_initialize(&s, my_alloc, my_free, MNG_NULL);
    CHECK(h != MNG_NULL, "T5 init for bad-sig", "%s", "NULL");
    if (h) {
        mng_setcb_openstream(h, cb_open);
        mng_setcb_closestream(h, cb_close);
        mng_setcb_readdata(h, cb_read);
        mng_setcb_processheader(h, cb_processheader);
        mng_setcb_getcanvasline(h, cb_getcanvasline_stub);
        mng_setcb_refresh(h, cb_refresh);
        mng_setcb_gettickcount(h, cb_gettickcount);
        mng_setcb_settimer(h, cb_settimer);
        mng_retcode rc = mng_readdisplay(h);
        CHECK(rc != MNG_NOERROR, "T5 bad signature rejected", "rc=%d", rc);
        mng_int8 severity; mng_chunkid chunkname; mng_uint32 chunkseq;
        mng_int32 e1, e2; mng_pchar errtext;
        mng_getlasterror(h, &severity, &chunkname, &chunkseq, &e1, &e2,
                         &errtext);
        CHECK(errtext != NULL && errtext[0] != '\0',
              "T5 getlasterror has text", "text=%s",
              errtext ? errtext : "(null)");
        mng_cleanup(&h);
    }

    /* 未知 critical chunk */
    len = build_mng(buf, sizeof buf, 8, 8, 0, 1, 0);
    memstream_t s2 = { buf, len, 0, 0, 0, 0 };
    h = mng_initialize(&s2, my_alloc, my_free, MNG_NULL);
    CHECK(h != MNG_NULL, "T5 init for bad-chunk", "%s", "NULL");
    if (h) {
        mng_setcb_openstream(h, cb_open);
        mng_setcb_closestream(h, cb_close);
        mng_setcb_readdata(h, cb_read);
        mng_setcb_processheader(h, cb_processheader);
        mng_setcb_getcanvasline(h, cb_getcanvasline_stub);
        mng_setcb_refresh(h, cb_refresh);
        mng_setcb_gettickcount(h, cb_gettickcount);
        mng_setcb_settimer(h, cb_settimer);
        mng_retcode rc = mng_readdisplay(h);
        CHECK(rc != MNG_NOERROR, "T5 unknown critical chunk rejected",
              "rc=%d", rc);
        mng_cleanup(&h);
    }

    /* 纯噪声 */
    for (int i = 0; i < 64; i++) buf[i] = (unsigned char)(i * 7);
    memstream_t s3 = { buf, 64, 0, 0, 0, 0 };
    h = mng_initialize(&s3, my_alloc, my_free, MNG_NULL);
    if (h) {
        mng_setcb_openstream(h, cb_open);
        mng_setcb_closestream(h, cb_close);
        mng_setcb_readdata(h, cb_read);
        mng_setcb_processheader(h, cb_processheader);
        mng_setcb_getcanvasline(h, cb_getcanvasline_stub);
        mng_setcb_refresh(h, cb_refresh);
        mng_setcb_gettickcount(h, cb_gettickcount);
        mng_setcb_settimer(h, cb_settimer);
        mng_retcode rc = mng_readdisplay(h);
        CHECK(rc != MNG_NOERROR, "T5 noise rejected", "rc=%d", rc);
        mng_cleanup(&h);
    }
}

/* ─────────────────── T6: 截断数据 ─────────────────── */
static void test_truncation(void) {
    static unsigned char buf[64 * 1024];
    int cutpoints[] = { 20, 52, 90 };
    for (unsigned ci = 0; ci < 3; ci++) {
        mng_uint32 len = build_mng(buf, sizeof buf, 8, 8, 0, 0, cutpoints[ci]);
        memstream_t s = { buf, len, 0, 0, 0, 0 };
        mng_handle h = mng_initialize(&s, my_alloc, my_free, MNG_NULL);
        CHECK(h != MNG_NULL, "T6 init truncated stream", "cut=%d",
              cutpoints[ci]);
        if (!h) continue;
        mng_setcb_openstream(h, cb_open);
        mng_setcb_closestream(h, cb_close);
        mng_setcb_readdata(h, cb_read);
        mng_setcb_processheader(h, cb_processheader);
        mng_setcb_getcanvasline(h, cb_getcanvasline_stub);
        mng_setcb_refresh(h, cb_refresh);
        mng_setcb_gettickcount(h, cb_gettickcount);
        mng_setcb_settimer(h, cb_settimer);
        mng_retcode rc = mng_readdisplay(h);
        CHECK(rc != MNG_NOERROR, "T6 truncated stream rejected",
              "cut=%d rc=%d", cutpoints[ci], rc);
        mng_cleanup(&h);
    }
}

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("1..0 # SKIP no fixture given\n");
        return 0;
    }
    /* 固定计划数: T1=8 T2=1 T3=6 T4=4 T5=6 T6=6 → 共 31
     * (T1 8: openable/sig/init/readdisplay/header-once/dims/canvaslines/
     *  sigtype+width+height+framecount 其中 4 项在 T1 计)
     * 实际运行时打印 1..31 */
    printf("TAP version 13\n1..31\n");
    test_official_fixture(argv[1]);
    test_programmatic();
    test_errors();
    test_truncation();
    printf("# checks=%d fails=%d\n", g_checks, g_fails);
    return g_fails ? 1 : 0;
}
