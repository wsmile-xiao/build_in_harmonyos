/*
 * test_libsmacker.c — consumer assertion test for libsmacker (HarmonyOS PC).
 *
 * What this is
 * ------------
 * Upstream libsmacker 1.1.1r35 ships NO test suite: there is no tests/
 * directory, no TESTS/check_PROGRAMS in Makefile.am (so `make check` is
 * automake's empty default target), and no assertion framework anywhere in
 * the sources.  The two shipped programs, driver.c and smk2avi.c, are demo
 * applications: driver.c prints metadata and writes BMP files, and returns 0
 * unconditionally on success without checking anything.
 *
 * This test adapts driver.c's call sequence
 *     smk_open_* -> smk_info_* -> smk_enable_* -> smk_first -> smk_get_*
 *     -> dump_bmp() -> smk_close()
 * into a real assertion consumer: every step is checked and counted, and the
 * "write a file and walk away" step of the demo is replaced by assertions on
 * the bytes that were written.
 *
 * Input
 * -----
 * synthetic.smk is produced by gen_smk.py (same directory), a byte-exact
 * implementation of the layout documented in upstream smacker.c
 * (smk_open_generic) and smk_hufftree.c.  It is an 8x8, 1 frame, video only,
 * SOLID-BLOCK clip, so a correct decode must yield 64 bytes of a single
 * colour.  Nothing is downloaded and no binary fixture is committed.
 *
 * Exit code is 0 only when every check passed.
 */
#include "smacker.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define FRAME_W 8
#define FRAME_H 8
#define SOLID_COLOR 0x20
#define BMP_HEADER_SIZE 1078 /* 14 + 40 + 256 * 4, see dump_bmp() */

static int g_checks = 0;
static int g_fails = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        g_checks++;                                                          \
        if (cond) {                                                          \
            printf("ok %d - %s\n", g_checks, (msg));                         \
        } else {                                                             \
            g_fails++;                                                       \
            printf("FAIL %d - %s (%s:%d)\n", g_checks, (msg), __FILE__,      \
                   __LINE__);                                                \
        }                                                                    \
    } while (0)

/* Read a whole file into a malloc'd buffer. */
static unsigned char *slurp(const char *path, size_t *out_len)
{
    FILE *f = fopen(path, "rb");
    unsigned char *buf;
    long size;

    *out_len = 0;
    if (!f) {
        return NULL;
    }
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    size = ftell(f);
    if (size <= 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    buf = (unsigned char *)malloc((size_t)size);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    if (fread(buf, 1, (size_t)size, f) != (size_t)size) {
        free(buf);
        fclose(f);
        return NULL;
    }
    fclose(f);
    *out_len = (size_t)size;
    return buf;
}

/*
 * dump_bmp() — taken verbatim in behaviour from upstream driver.c, except
 * that the destination file name is a plain path in the current directory
 * (the demo's hardcoded "bmp/" subdirectory would need a pre-created dir).
 * Returns 0 on success so the caller can assert on it; upstream ignores
 * every error here.
 */
static int dump_bmp(const unsigned char *pal, const unsigned char *image,
                    unsigned int w, unsigned int h, const char *path)
{
    unsigned int i;
    FILE *fp;
    unsigned int temp;

    fp = fopen(path, "wb");
    if (!fp) {
        return -1;
    }
    fwrite("BM", 2, 1, fp);
    temp = BMP_HEADER_SIZE + (w * h);
    fwrite(&temp, 4, 1, fp);
    temp = 0;
    fwrite(&temp, 4, 1, fp);
    temp = BMP_HEADER_SIZE;
    fwrite(&temp, 4, 1, fp);
    temp = 40;
    fwrite(&temp, 4, 1, fp);
    fwrite(&w, 4, 1, fp);
    fwrite(&h, 4, 1, fp);
    temp = 1;
    fwrite(&temp, 2, 1, fp);
    temp = 8;
    fwrite(&temp, 4, 1, fp);
    temp = 0;
    fwrite(&temp, 2, 1, fp);
    temp = w * h;
    fwrite(&temp, 4, 1, fp);
    temp = 0;
    fwrite(&temp, 4, 1, fp);
    fwrite(&temp, 4, 1, fp);
    temp = 256;
    fwrite(&temp, 4, 1, fp);
    temp = 256;
    fwrite(&temp, 4, 1, fp);
    temp = 0;
    for (i = 0; i < 256; i++) {
        fwrite(&pal[(i * 3) + 2], 1, 1, fp);
        fwrite(&pal[(i * 3) + 1], 1, 1, fp);
        fwrite(&pal[(i * 3)], 1, 1, fp);
        fwrite(&temp, 1, 1, fp);
    }
    for (i = h; i > 0; i--) {
        fwrite(&image[(i - 1) * w], w, 1, fp);
    }
    if (fclose(fp) != 0) {
        return -1;
    }
    return 0;
}

/* Count pixels that are not the expected solid colour. */
static size_t wrong_pixels(const unsigned char *buf, size_t len,
                           unsigned char want)
{
    size_t i, bad = 0;
    for (i = 0; i < len; i++) {
        if (buf[i] != want) {
            bad++;
        }
    }
    return bad;
}

int main(int argc, char **argv)
{
    const char *path;
    unsigned char *data;
    size_t len = 0;
    smk s = NULL, s_disk = NULL, s_mem_file = NULL;
    unsigned long w = 0, h = 0, frame = 0, frames = 0;
    unsigned char y_scale = 0xFF, track_mask = 0xFF;
    unsigned char channels[7], bitdepth[7];
    unsigned long rate[7];
    double usf = 0.0;
    const unsigned char *pix;
    const unsigned char *pal;
    unsigned char *bad;
    char bmp_path[] = "libsmacker_test_out.bmp";
    FILE *bf;
    long bmp_size;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <file.smk>\n", argv[0]);
        return 2;
    }
    path = argv[1];

    /* Line-buffer stdout so every "ok N" line is flushed before the next
     * call into libsmacker; otherwise stdout (block-buffered when the test
     * runs under `conan create`) interleaves with libsmacker's stderr
     * diagnostics and the captured log is unreadable. */
    setvbuf(stdout, NULL, _IOLBF, 0);

    /* ---- A. input fixture ------------------------------------------- */
    data = slurp(path, &len);
    CHECK(data != NULL, "synthetic.smk can be read from disk");
    if (!data) {
        printf("1..%d\n", g_checks);
        return 1;
    }
    CHECK(len > 100, "synthetic.smk is larger than a bare header");

    /* ---- B. memory-mode open + metadata ----------------------------- */
    s = smk_open_memory(data, (unsigned long)len);
    CHECK(s != NULL, "smk_open_memory accepts the synthesised clip");
    if (!s) {
        printf("1..%d\n", g_checks);
        free(data);
        return 1;
    }

    CHECK(smk_info_all(s, &frame, &frames, &usf) == 0,
          "smk_info_all returns success");
    CHECK(frames == 1, "frame count parsed as 1");
    CHECK(frame == 0, "initial frame index is 0");
    CHECK(usf == 40000.0, "microseconds-per-frame parsed as 40000 (25 fps)");

    CHECK(smk_info_video(s, &w, &h, &y_scale) == 0,
          "smk_info_video returns success");
    CHECK(w == FRAME_W, "width parsed as 8");
    CHECK(h == FRAME_H, "height parsed as 8");
    CHECK(y_scale == SMK_FLAG_Y_NONE, "y-scale mode parsed as SMK_FLAG_Y_NONE");

    CHECK(smk_info_audio(s, &track_mask, channels, bitdepth, rate) == 0,
          "smk_info_audio returns success");
    CHECK(track_mask == 0, "no audio tracks in the synthesised clip");

    pal = smk_get_palette(s);
    CHECK(pal != NULL, "smk_get_palette returns a palette buffer");
    CHECK(smk_get_video(s) != NULL, "smk_get_video returns a frame buffer");

    /* ---- C. enable + render + decode -------------------------------- */
    CHECK(smk_enable_video(s, 1) == 0, "smk_enable_video(1) returns success");
    CHECK(smk_enable_all(s, SMK_VIDEO_TRACK) == 0,
          "smk_enable_all(SMK_VIDEO_TRACK) returns success");
    CHECK(smk_first(s) == SMK_LAST,
          "smk_first reports SMK_LAST for a single-frame clip");

    pix = smk_get_video(s);
    CHECK(pix != NULL, "frame buffer is non-NULL after smk_first");
    if (pix) {
        bad = (unsigned char *)malloc((size_t)(FRAME_W * FRAME_H));
        memcpy(bad, pix, (size_t)(FRAME_W * FRAME_H));
        CHECK(wrong_pixels(bad, (size_t)(FRAME_W * FRAME_H), SOLID_COLOR) == 0,
              "all 64 decoded pixels equal the encoded solid colour 0x20");
        free(bad);
    }

    CHECK(smk_info_all(s, &frame, NULL, NULL) == 0,
          "smk_info_all still succeeds after rendering");
    CHECK(frame == 0, "frame index still 0 after smk_first");

    CHECK(smk_seek_keyframe(s, 0) == 0, "smk_seek_keyframe(0) returns success");
    pix = smk_get_video(s);
    CHECK(pix && wrong_pixels(pix, (size_t)(FRAME_W * FRAME_H),
                              SOLID_COLOR) == 0,
          "frame content unchanged after smk_seek_keyframe");

    /* f == 1 and no ring frame => nothing to advance to. */
    CHECK(smk_next(s) == SMK_DONE,
          "smk_next returns SMK_DONE at the end of a 1-frame clip");

    /* ---- D. the three upstream open entry points --------------------- */
    s_disk = smk_open_file(path, SMK_MODE_DISK);
    CHECK(s_disk != NULL, "smk_open_file(SMK_MODE_DISK) opens the clip");
    if (s_disk) {
        w = h = 0;
        frames = 0;
        CHECK(smk_info_video(s_disk, &w, &h, NULL) == 0 && w == FRAME_W
                  && h == FRAME_H,
              "disk-mode metadata matches (8x8)");
        CHECK(smk_info_all(s_disk, NULL, &frames, NULL) == 0 && frames == 1,
              "disk-mode frame count matches");
        CHECK(smk_enable_video(s_disk, 1) == 0,
              "disk-mode smk_enable_video succeeds");
        CHECK(smk_first(s_disk) == SMK_LAST,
              "disk-mode smk_first renders the frame");
        pix = smk_get_video(s_disk);
        CHECK(pix && wrong_pixels(pix, (size_t)(FRAME_W * FRAME_H),
                                  SOLID_COLOR) == 0,
              "disk-mode decode yields the same solid colour frame");
        smk_close(s_disk);
    }

    s_mem_file = smk_open_file(path, SMK_MODE_MEMORY);
    CHECK(s_mem_file != NULL,
          "smk_open_file(SMK_MODE_MEMORY) opens the clip (driver.c path)");
    if (s_mem_file) {
        smk_close(s_mem_file);
    }

    /* ---- E. negative / malformed input ------------------------------ */
    CHECK(smk_open_memory((const unsigned char *)"NOTASMK0000", 11) == NULL,
          "smk_open_memory rejects a bad signature");
    CHECK(smk_open_memory(data, (unsigned long)(len / 2)) == NULL,
          "smk_open_memory rejects a truncated file");
    CHECK(smk_open_file("/nonexistent/path/nope.smk", SMK_MODE_DISK) == NULL,
          "smk_open_file rejects a missing file");

    /* ---- F. BMP dump path (driver.c) turned into assertions --------- */
    pal = smk_get_palette(s);
    pix = smk_get_video(s);
    CHECK(dump_bmp(pal, pix, (unsigned int)FRAME_W, (unsigned int)FRAME_H,
                   bmp_path) == 0,
          "dump_bmp (driver.c) writes the output file");

    bf = fopen(bmp_path, "rb");
    CHECK(bf != NULL, "output BMP exists");
    bmp_size = -1;
    if (bf) {
        char magic[2] = {0, 0};
        CHECK(fread(magic, 1, 2, bf) == 2 && magic[0] == 'B' && magic[1] == 'M',
              "BMP magic is 'BM'");
        fseek(bf, 0, SEEK_END);
        bmp_size = ftell(bf);
        fclose(bf);
        CHECK(bmp_size == (long)(BMP_HEADER_SIZE + FRAME_W * FRAME_H),
              "BMP size equals 1078 + w*h bytes");
    }
    if (bmp_size > 0) {
        size_t blen = 0;
        unsigned char *bmp = slurp(bmp_path, &blen);
        CHECK(bmp != NULL && blen == (size_t)bmp_size,
              "BMP can be read back");
        if (bmp) {
            CHECK(blen > BMP_HEADER_SIZE
                      && wrong_pixels(bmp + BMP_HEADER_SIZE,
                                      blen - BMP_HEADER_SIZE,
                                      SOLID_COLOR) == 0,
                  "every BMP pixel equals the decoded solid colour");
            free(bmp);
        }
    }

    /* ---- teardown --------------------------------------------------- */
    smk_close(s);
    free(data);

    printf("1..%d\n", g_checks);
    printf("# libsmacker consumer test: %d checks, %d failures\n", g_checks,
           g_fails);
    return g_fails == 0 ? 0 : 1;
}
