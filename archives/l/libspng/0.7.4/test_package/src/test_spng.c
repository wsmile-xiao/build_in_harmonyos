#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <zlib.h>
#include <spng.h>

/* ============================================================
 * libspng 0.7.4 test_package
 * All PNGs are built in-memory (zlib deflate + hand-written chunks).
 * No external binary files: CI checkout-pr cannot apply binary diffs.
 *
 * Subcommands (each is one CTest):
 *   rgba8      - RGBA8 decode round-trip            (upstream behavior)
 *   gray8      - grayscale PNG decode               (UPSTREAM-derived)
 *   rgb        - RGB PNG decode                     (UPSTREAM-derived)
 *   palette    - indexed-color PNG decode           (NEW test)
 *   corrupt    - bad-CRC PNG must be rejected       (NEW: error path)
 *   truncated  - truncated stream must be rejected  (NEW: error path)
 *   api        - version/API edge cases             (NEW: API boundary)
 * ============================================================ */

typedef struct {
    unsigned char *buf;
    size_t len;
} PngBuf;

static unsigned int be32(const unsigned char *p)
{
    return ((unsigned int)p[0] << 24) | (p[1] << 16) | (p[2] << 8) | p[3];
}

static void put32(unsigned char *p, unsigned int v)
{
    p[0] = (v >> 24) & 0xff; p[1] = (v >> 16) & 0xff;
    p[2] = (v >> 8) & 0xff;  p[3] = v & 0xff;
}

static void put_crc(unsigned char *p, uLong crc)
{
    p[0] = (crc >> 24) & 0xff; p[1] = (crc >> 16) & 0xff;
    p[2] = (crc >> 8) & 0xff;  p[3] = crc & 0xff;
}

/* Append a PNG chunk (type + data) to growable buffer. */
static void append_chunk(PngBuf *png, const char *type,
                         const unsigned char *data, unsigned int dlen)
{
    size_t need = png->len + 12 + dlen;
    png->buf = realloc(png->buf, need);
    unsigned char *p = png->buf + png->len;
    put32(p, dlen);
    memcpy(p + 4, type, 4);
    if (dlen) memcpy(p + 8, data, dlen);
    uLong crc = crc32(0L, Z_NULL, 0);
    crc = crc32(crc, (const Bytef *)type, 4);
    if (dlen) crc = crc32(crc, data, dlen);
    put_crc(p + 8 + dlen, crc);
    png->len = need;
}

/* Build PNG with given ihdr values. raw=deflated payload bytes (may be NULL
 * to emit an empty IDAT). rows pixels in scanlines with filter byte 0. */
static PngBuf build_png(unsigned int w, unsigned int h, int bit_depth,
                        int color_type, const unsigned char *scanlines,
                        size_t scan_len)
{
    PngBuf png = { NULL, 0 };
    static const unsigned char sig[8] = {0x89,'P','N','G','\r','\n',0x1a,'\n'};
    png.buf = malloc(64); png.len = 0;
    memcpy(png.buf, sig, 8); png.len = 8;

    unsigned char ihdr[13];
    put32(ihdr, w); put32(ihdr + 4, h);
    ihdr[8] = (unsigned char)bit_depth;
    ihdr[9] = (unsigned char)color_type;
    ihdr[10] = 0; ihdr[11] = 0; ihdr[12] = 0;
    append_chunk(&png, "IHDR", ihdr, 13);

    uLongf idat_len = compressBound(scan_len);
    unsigned char *idat = malloc(idat_len ? idat_len : 1);
    if (scan_len) {
        compress2(idat, &idat_len, scanlines, (uLong)scan_len, 6);
    } else {
        idat_len = 0;
    }
    append_chunk(&png, "IDAT", idat, (unsigned int)idat_len);
    free(idat);
    append_chunk(&png, "IEND", NULL, 0);
    return png;
}

/* scanlines for raw RGBA/RGB/Gray data with filter byte 0 prefix per row */
static unsigned char *make_scanlines(unsigned int w, unsigned int h,
                                     int bpp, unsigned int seed)
{
    unsigned char *raw = malloc((size_t)h * (1 + (size_t)w * bpp));
    size_t row = 1 + (size_t)w * bpp;
    for (unsigned int y = 0; y < h; y++) {
        raw[y * row] = 0;
        for (unsigned int x = 0; x < w; x++) {
            unsigned char *px = raw + y * row + 1 + (size_t)x * bpp;
            unsigned int v = (x * 255 / (w ? w - 1 : 1)) ^ seed;
            for (int c = 0; c < bpp; c++) px[c] = (unsigned char)(v + c * 17 + y);
        }
    }
    return raw;
}

/* pixel-stream compare: ref_raw has per-row filter prefix, out is pure pixels */
static int pixels_equal(const unsigned char *ref_raw, unsigned int w, unsigned int h,
                        int bpp, const unsigned char *out)
{
    size_t row = 1 + (size_t)w * bpp;
    for (unsigned int y = 0; y < h; y++) {
        if (memcmp(ref_raw + y * row + 1, out + y * (size_t)w * bpp,
                   (size_t)w * bpp) != 0)
            return 0;
    }
    return 1;
}

static int check(int cond, const char *what)
{
    if (!cond) { fprintf(stderr, "FAIL: %s\n", what); return 1; }
    return 0;
}

/* decode helper: returns 0 on success, fills out/dsz */
static int decode_all(const PngBuf *png, int out_fmt,
                      unsigned char **out, size_t *dsz)
{
    spng_ctx *dec = spng_ctx_new(0);
    if (!dec) return -1;
    int r = spng_set_png_buffer(dec, png->buf, png->len);
    if (r) { spng_ctx_free(dec); return r; }
    r = spng_decoded_image_size(dec, out_fmt, dsz);
    if (r) { spng_ctx_free(dec); return r; }
    *out = malloc(*dsz ? *dsz : 1);
    r = spng_decode_image(dec, *out, *dsz, out_fmt, 0);
    spng_ctx_free(dec);
    return r;
}

static int t_rgba8(void)
{
    const unsigned w = 8, h = 8, bpp = 4;
    int rc = 0;
    const char *ver = spng_version_string();
    rc |= check(ver && ver[0], "version string non-empty");
    unsigned char *raw = make_scanlines(w, h, bpp, 0x5a);
    PngBuf png = build_png(w, h, 8, SPNG_COLOR_TYPE_TRUECOLOR_ALPHA,
                           raw, (size_t)h * (1 + w * bpp));
    free(raw);
    unsigned char *out = NULL; size_t dsz = 0;
    int r = decode_all(&png, SPNG_FMT_RGBA8, &out, &dsz);
    rc |= check(r == 0, "rgba8 decode ok");
    rc |= check(dsz == w * h * 4, "rgba8 size");
    unsigned char *ref = make_scanlines(w, h, bpp, 0x5a);
    rc |= check(pixels_equal(ref, w, h, bpp, out), "rgba8 pixels identical");
    free(ref);
    free(out); free(png.buf);
    return rc;
}

static int t_gray8(void)
{
    const unsigned w = 16, h = 16, bpp = 1;
    int rc = 0;
    unsigned char *raw = make_scanlines(w, h, bpp, 0x21);
    PngBuf png = build_png(w, h, 8, SPNG_COLOR_TYPE_GRAYSCALE,
                           raw, (size_t)h * (1 + w * bpp));
    free(raw);
    unsigned char *out = NULL; size_t dsz = 0;
    int r = decode_all(&png, SPNG_FMT_G8, &out, &dsz);
    rc |= check(r == 0, "gray8 decode ok");
    rc |= check(dsz == w * h, "gray8 size");
    unsigned char *ref = make_scanlines(w, h, bpp, 0x21);
    rc |= check(pixels_equal(ref, w, h, bpp, out), "gray8 pixels identical");
    free(ref); free(out); free(png.buf);
    return rc;
}

static int t_rgb(void)
{
    const unsigned w = 12, h = 9, bpp = 3;
    int rc = 0;
    unsigned char *raw = make_scanlines(w, h, bpp, 0x99);
    PngBuf png = build_png(w, h, 8, SPNG_COLOR_TYPE_TRUECOLOR,
                           raw, (size_t)h * (1 + w * bpp));
    free(raw);
    unsigned char *out = NULL; size_t dsz = 0;
    int r = decode_all(&png, SPNG_FMT_RGB8, &out, &dsz);
    rc |= check(r == 0, "rgb decode ok");
    rc |= check(dsz == w * h * 3, "rgb size");
    unsigned char *ref = make_scanlines(w, h, bpp, 0x99);
    rc |= check(pixels_equal(ref, w, h, bpp, out), "rgb pixels identical");
    free(ref); free(out); free(png.buf);
    return rc;
}

static int t_palette(void)
{
    /* indexed PNG: 2-color palette, 4x4, pixel indices 0/1 pattern */
    const unsigned w = 4, h = 4;
    int rc = 0;
    unsigned char plte[6] = { 0x10, 0x20, 0x30,  0xE0, 0xD0, 0xC0 };
    /* raw: filter + indices */
    unsigned char raw[4 * (1 + 4)];
    for (unsigned int y = 0; y < h; y++) {
        raw[y * 5] = 0;
        for (unsigned int x = 0; x < w; x++) raw[y * 5 + 1 + x] = (x + y) % 2;
    }
    PngBuf png = { NULL, 0 };
    png.buf = malloc(8); png.len = 8;
    memcpy(png.buf, "\x89PNG\r\n\x1a\n", 8);
    unsigned char ihdr[13];
    put32(ihdr, w); put32(ihdr + 4, h);
    ihdr[8] = 8; ihdr[9] = SPNG_COLOR_TYPE_INDEXED;
    ihdr[10] = ihdr[11] = ihdr[12] = 0;
    append_chunk(&png, "IHDR", ihdr, 13);
    append_chunk(&png, "PLTE", plte, 6);
    uLongf idat_len = compressBound(sizeof(raw));
    unsigned char *idat = malloc(idat_len);
    compress2(idat, &idat_len, raw, sizeof(raw), 6);
    append_chunk(&png, "IDAT", idat, (unsigned int)idat_len);
    free(idat);
    append_chunk(&png, "IEND", NULL, 0);

    unsigned char *out = NULL; size_t dsz = 0;
    int r = decode_all(&png, SPNG_FMT_RGBA8, &out, &dsz);
    rc |= check(r == 0, "palette decode ok");
    rc |= check(dsz == w * h * 4, "palette rgba8 size");
    if (!rc) {
        /* pixel (0,0)=idx0 -> plte[0..2] 0x10,0x20,0x30 */
        rc |= check(out[0] == 0x10 && out[1] == 0x20 && out[2] == 0x30 &&
                    out[3] == 0xff, "palette color 0 correct");
        /* pixel (1,0): idx=(1+0)%2=1 -> plte[3..5] 0xe0,0xd0,0xc0 */
        rc |= check(out[4] == 0xe0 && out[5] == 0xd0 && out[6] == 0xc0 &&
                    out[7] == 0xff, "palette color 1 correct");
    }
    free(out); free(png.buf);
    return rc;
}

static int t_corrupt(void)
{
    /* flip one CRC byte -> decode must fail cleanly (no crash) */
    const unsigned w = 8, h = 8, bpp = 4;
    int rc = 0;
    unsigned char *raw = make_scanlines(w, h, bpp, 1);
    PngBuf png = build_png(w, h, 8, SPNG_COLOR_TYPE_TRUECOLOR_ALPHA,
                           raw, (size_t)h * (1 + w * bpp));
    free(raw);
    /* find IHDR chunk end = sig(8) + len4(4) + type(4) + data(13) + crc(4) -> crc at 8+4+4+13=29 */
    if (png.len > 30) png.buf[29] ^= 0xff; /* corrupt IHDR crc */
    spng_ctx *dec = spng_ctx_new(0);
    rc |= check(dec != NULL, "ctx");
    if (dec) {
        int r = spng_set_png_buffer(dec, png.buf, png.len);
        rc |= check(r == 0, "set buffer on corrupt png");
        unsigned char *out = NULL; size_t dsz = 0;
        r = spng_decoded_image_size(dec, SPNG_FMT_RGBA8, &dsz);
        if (r == 0) {
            out = malloc(dsz ? dsz : 1);
            r = spng_decode_image(dec, out, dsz, SPNG_FMT_RGBA8, 0);
        }
        free(out);
        rc |= check(r != 0, "corrupt PNG rejected with error");
        spng_ctx_free(dec);
    }
    free(png.buf);
    return rc;
}

static int t_truncated(void)
{
    /* valid PNG truncated mid-IDAT -> decode must fail cleanly */
    const unsigned w = 32, h = 32, bpp = 4;
    int rc = 0;
    unsigned char *raw = make_scanlines(w, h, bpp, 7);
    PngBuf png = build_png(w, h, 8, SPNG_COLOR_TYPE_TRUECOLOR_ALPHA,
                           raw, (size_t)h * (1 + w * bpp));
    free(raw);
    size_t cut = png.len / 2;
    if (cut > 24 && cut < png.len) {
        spng_ctx *dec = spng_ctx_new(0);
        if (dec) {
            int r = spng_set_png_buffer(dec, png.buf, cut);
            unsigned char *out = NULL; size_t dsz = 0;
            if (r == 0) r = spng_decoded_image_size(dec, SPNG_FMT_RGBA8, &dsz);
            if (r == 0 && dsz) {
                out = malloc(dsz);
                r = spng_decode_image(dec, out, dsz, SPNG_FMT_RGBA8, 0);
            }
            free(out);
            rc |= check(r != 0, "truncated PNG rejected");
            spng_ctx_free(dec);
        }
    } else {
        rc |= check(0, "png too small to truncate");
    }
    free(png.buf);
    return rc;
}

static int t_api(void)
{
    int rc = 0;
    /* NULL context safety */
    rc |= check(spng_get_ihdr(NULL, NULL) != 0, "NULL ctx rejected");
    /* version API */
    const char *v = spng_version_string();
    rc |= check(v != NULL && strlen(v) > 3, "version string length");
    /* ctx_new with bogus flags is tolerated, but new(0) decoder works */
    spng_ctx *d1 = spng_ctx_new(0);
    spng_ctx *d2 = spng_ctx_new(SPNG_CTX_ENCODER);
    rc |= check(d1 != NULL && d2 != NULL, "ctx creation");
    /* decode before buffer set must error, not crash */
    if (d1) {
        unsigned char tmp[16];
        size_t s = sizeof(tmp);
        int r = spng_decode_image(d1, tmp, s, SPNG_FMT_RGBA8, 0);
        rc |= check(r != 0, "decode without source errors");
        spng_ctx_free(d1);
    }
    if (d2) spng_ctx_free(d2);
    /* decoded_image_size on empty ctx */
    spng_ctx *e = spng_ctx_new(0);
    if (e) {
        size_t s2 = 0;
        rc |= check(spng_decoded_image_size(e, SPNG_FMT_RGBA8, &s2) != 0,
                    "size without source errors");
        spng_ctx_free(e);
    }
    return rc;
}

int main(int argc, char **argv)
{
    const char *which = argc > 1 ? argv[1] : "rgba8";
    int rc = 0;
    if (strcmp(which, "rgba8") == 0) rc = t_rgba8();
    else if (strcmp(which, "gray8") == 0) rc = t_gray8();
    else if (strcmp(which, "rgb") == 0) rc = t_rgb();
    else if (strcmp(which, "palette") == 0) rc = t_palette();
    else if (strcmp(which, "corrupt") == 0) rc = t_corrupt();
    else if (strcmp(which, "truncated") == 0) rc = t_truncated();
    else if (strcmp(which, "api") == 0) rc = t_api();
    else { fprintf(stderr, "unknown subtest: %s\n", which); return 2; }
    if (rc == 0) printf("test[%s] PASS\n", which);
    return rc;
}
