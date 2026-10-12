/* test_package/test.c — gifdec 0.0-git.1dcbae1 consumer-side verification.
 *
 * gifdec upstream ships no test suite (example.c is an interactive SDL2
 * player, not a test), so this suite synthesizes minimal valid GIF89a
 * byte streams programmatically — header + logical screen descriptor +
 * 2-entry global color table + image descriptor + hand-packed LZW data —
 * writes them to a temp directory and drives the full public API of the
 * packaged library: gd_open_gif / gd_get_frame / gd_render_frame /
 * gd_is_bgcolor / gd_rewind / gd_close_gif.
 *
 * All assertion anchors were calibrated against the unmodified upstream
 * gifdec.c on OHOS aarch64 (clang 15) before being frozen here:
 * 49/49 checks pass. LZW streams below are LSB-first bit-packed by hand
 * (e.g. min-code-size 2: [clear][0] -> 0x04; [clear][0][1] -> 0x44 0x00).
 *
 * Usage: test_gifdec <writable-temp-dir>
 * Exit 0 = all assertions pass.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include "gifdec.h"

static int checks = 0;
static int failures = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (cond) { printf("CHECK passed: %s\n", msg); } \
    else { printf("CHECK FAILED: %s\n", msg); failures++; } \
} while (0)

static char tmpdir[512];

/* Write a byte buffer into the temp dir, return the full path. */
static const char *write_gif(const char *name, const uint8_t *buf, size_t len)
{
    static char path[600];
    FILE *f;
    snprintf(path, sizeof(path), "%s/%s", tmpdir, name);
    f = fopen(path, "wb");
    if (!f) { printf("CHECK FAILED: cannot open %s\n", path); exit(2); }
    fwrite(buf, 1, len, f);
    fclose(f);
    return path;
}

/* ── 1×1 black pixel: minimal complete GIF89a stream ──
 * LSD: GCT flag, color-res 7, size 0 -> 2 entries [black, red].
 * LZW (min code size 2): [clear=4][code 0] -> 6 bits -> byte 0x04. */
static const uint8_t GIF_1X1[] = {
    'G','I','F','8','9','a',
    0x01,0x00,              /* width = 1 */
    0x01,0x00,              /* height = 1 */
    0xF0,                   /* GCT present, color res 7, size field 0 */
    0x00,                   /* bgindex = 0 */
    0x00,                   /* aspect */
    0x00,0x00,0x00,         /* GCT[0] = black */
    0xFF,0x00,0x00,         /* GCT[1] = red */
    0x2C,                   /* image separator */
    0x00,0x00,              /* fx = 0 */
    0x00,0x00,              /* fy = 0 */
    0x01,0x00,              /* fw = 1 */
    0x01,0x00,              /* fh = 1 */
    0x00,                   /* packed: no LCT, no interlace */
    0x02,                   /* LZW min code size */
    0x01,                   /* sub-block length */
    0x04,                   /* LZW data: [clear][code 0] */
    0x00,                   /* block terminator */
    0x3B                    /* trailer */
};

/* ── 2×1 two colors: pixels [black, red]; bgindex = 1 ──
 * LZW: [clear=4][0][1] -> 9 bits LSB-first -> bytes 0x44 0x00. */
static const uint8_t GIF_2X1[] = {
    'G','I','F','8','9','a',
    0x02,0x00,
    0x01,0x00,
    0xF0,
    0x01,                   /* bgindex = 1 (red) */
    0x00,
    0x00,0x00,0x00,
    0xFF,0x00,0x00,
    0x2C,
    0x00,0x00,
    0x00,0x00,
    0x02,0x00,
    0x01,0x00,
    0x00,
    0x02,
    0x02,                   /* sub-block length */
    0x44,0x00,              /* LZW data: [clear][0][1] */
    0x00,
    0x3B
};

/* ── GCE + NETSCAPE loop extension before the image ──
 * GCE: delay = 10 (cs), no transparency. NETSCAPE2.0: loop count = 3. */
static const uint8_t GIF_EXT[] = {
    'G','I','F','8','9','a',
    0x02,0x00,
    0x01,0x00,
    0xF0,
    0x01,
    0x00,
    0x00,0x00,0x00,
    0xFF,0x00,0x00,
    0x21,0xF9,              /* extension: graphic control */
    0x04,                   /* block size */
    0x00,                   /* packed: disposal 0, no transparency */
    0x0A,0x00,              /* delay = 10 */
    0x00,                   /* transparent color index */
    0x00,                   /* block terminator */
    0x21,0xFF,              /* extension: application */
    0x0B,                   /* block size */
    'N','E','T','S','C','A','P','E',
    '2','.','0',
    0x03,                   /* sub-block size */
    0x01,                   /* sub-block ID */
    0x03,0x00,              /* loop count = 3 */
    0x00,                   /* block terminator */
    0x2C,
    0x00,0x00,
    0x00,0x00,
    0x02,0x00,
    0x01,0x00,
    0x00,
    0x02,
    0x02,
    0x44,0x00,
    0x00,
    0x3B
};

/* ── transparency: GCE tflag=1 tindex=1; GCT=[white,black]; bg=white;
 * frame [0,1]: pixel 1 == tindex -> skipped, canvas stays white ── */
static const uint8_t GIF_TRANSP[] = {
    'G','I','F','8','9','a',
    0x02,0x00,
    0x01,0x00,
    0xF0,
    0x00,                   /* bgindex = 0 (white) */
    0x00,
    0xFF,0xFF,0xFF,         /* GCT[0] = white */
    0x00,0x00,0x00,         /* GCT[1] = black */
    0x21,0xF9,
    0x04,
    0x01,                   /* packed: transparency flag set */
    0x00,0x00,              /* delay = 0 */
    0x01,                   /* tindex = 1 */
    0x00,
    0x2C,
    0x00,0x00,
    0x00,0x00,
    0x02,0x00,
    0x01,0x00,
    0x00,
    0x02,
    0x02,
    0x44,0x00,
    0x00,
    0x3B
};

/* ── local color table: frame palette [blue, green] overrides GCT ── */
static const uint8_t GIF_LCT[] = {
    'G','I','F','8','9','a',
    0x02,0x00,
    0x01,0x00,
    0xF0,
    0x00,
    0x00,
    0x00,0x00,0x00,         /* GCT[0] = black */
    0xFF,0x00,0x00,         /* GCT[1] = red */
    0x2C,
    0x00,0x00,
    0x00,0x00,
    0x02,0x00,
    0x01,0x00,
    0x80,                   /* packed: LCT flag, size field 0 -> 2 entries */
    0x00,0x00,0xFF,         /* LCT[0] = blue */
    0x00,0xFF,0x00,         /* LCT[1] = green */
    0x02,
    0x02,
    0x44,0x00,
    0x00,
    0x3B
};

/* ── two frames: f1 full 2×1 [black,red]; f2 1×1 black at (1,0) ──
 * default disposal keeps f1 pixels; f2 overwrites pixel[1]. */
static const uint8_t GIF_2FRAME[] = {
    'G','I','F','8','9','a',
    0x02,0x00,
    0x01,0x00,
    0xF0,
    0x00,
    0x00,
    0x00,0x00,0x00,
    0xFF,0x00,0x00,
    0x2C,                   /* frame 1 */
    0x00,0x00,
    0x00,0x00,
    0x02,0x00,
    0x01,0x00,
    0x00,
    0x02,
    0x02,
    0x44,0x00,
    0x00,
    0x2C,                   /* frame 2: fx=1, fy=0, 1×1 */
    0x01,0x00,
    0x00,0x00,
    0x01,0x00,
    0x01,0x00,
    0x00,
    0x02,
    0x01,
    0x04,
    0x00,
    0x3B
};

/* ── error-path streams ── */
static const uint8_t GIF_BADSIG[] = {
    'B','A','D','8','9','a',
    0x01,0x00, 0x01,0x00, 0xF0, 0x00, 0x00,
    0x00,0x00,0x00, 0x00,0x00,0x00,
    0x3B
};

static const uint8_t GIF_NOGCT[] = {
    'G','I','F','8','9','a',
    0x01,0x00, 0x01,0x00,
    0x00,                   /* GCT flag clear — upstream limitation */
    0x00, 0x00,
    0x3B
};

static const uint8_t GIF_87A[] = {
    'G','I','F','8','7','a',
    0x01,0x00, 0x01,0x00, 0xF0, 0x00, 0x00,
    0x00,0x00,0x00, 0xFF,0x00,0x00,
    0x2C, 0x00,0x00, 0x00,0x00, 0x01,0x00, 0x01,0x00, 0x00,
    0x02, 0x01, 0x04, 0x00,
    0x3B
};

static const uint8_t GIF_BADSEP[] = {
    'G','I','F','8','9','a',
    0x01,0x00, 0x01,0x00, 0xF0, 0x00, 0x00,
    0x00,0x00,0x00, 0xFF,0x00,0x00,
    0x58,                   /* 'X' garbage separator */
    0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
    0x3B
};

int main(int argc, char **argv)
{
    gd_GIF *gif;
    uint8_t frame[64];
    int ret;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <writable-temp-dir>\n", argv[0]);
        return 2;
    }
    snprintf(tmpdir, sizeof(tmpdir), "%s", argv[1]);

    /* ── open error contract ── */
    gif = gd_open_gif("/nonexistent/path/xyz.gif");
    CHECK(gif == NULL, "gd_open_gif(nonexistent) returns NULL");

    gif = gd_open_gif(write_gif("bad_signature.gif", GIF_BADSIG, sizeof(GIF_BADSIG)));
    CHECK(gif == NULL, "gd_open_gif(bad signature) returns NULL");

    gif = gd_open_gif(write_gif("no_gct.gif", GIF_NOGCT, sizeof(GIF_NOGCT)));
    CHECK(gif == NULL, "gd_open_gif(no global color table) returns NULL");

    gif = gd_open_gif(write_gif("gif87a.gif", GIF_87A, sizeof(GIF_87A)));
    CHECK(gif == NULL, "gd_open_gif(GIF87a version) returns NULL (89a only)");

    gif = gd_open_gif(write_gif("bad_separator.gif", GIF_BADSEP, sizeof(GIF_BADSEP)));
    CHECK(gif != NULL, "gd_open_gif(garbage separator stream) still opens");
    if (gif) {
        ret = gd_get_frame(gif);
        CHECK(ret == -1, "gd_get_frame(garbage separator) returns -1");
        gd_close_gif(gif);
    }

    /* ── 1×1 minimal GIF: header parse + single pixel decode ── */
    gif = gd_open_gif(write_gif("one_by_one.gif", GIF_1X1, sizeof(GIF_1X1)));
    CHECK(gif != NULL, "gd_open_gif(1x1 minimal) opens");
    if (gif) {
        CHECK(gif->width == 1, "parsed width == 1");
        CHECK(gif->height == 1, "parsed height == 1");
        CHECK(gif->depth == 8, "parsed depth == 8 (FDSZ color resolution)");
        CHECK(gif->palette->size == 2, "GCT size == 2 entries");
        CHECK(gif->bgindex == 0, "bgindex == 0");
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "gd_get_frame(frame 1) returns 1");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0x00,
              "1x1 pixel renders GCT[0] black (0,0,0)");
        ret = gd_get_frame(gif);
        CHECK(ret == 0, "gd_get_frame(trailer) returns 0");
        gd_rewind(gif);
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "gd_rewind + gd_get_frame re-decodes frame");
        gd_close_gif(gif);
    }

    /* ── 2×1 two-color GIF: LZW multi-code decode + bgcolor query ── */
    gif = gd_open_gif(write_gif("two_by_one.gif", GIF_2X1, sizeof(GIF_2X1)));
    CHECK(gif != NULL, "gd_open_gif(2x1) opens");
    if (gif) {
        CHECK(gif->width == 2 && gif->height == 1, "2x1 dimensions parsed");
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "2x1 gd_get_frame returns 1");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0x00,
              "pixel[0] == black (LZW code 0)");
        CHECK(frame[3] == 0xFF && frame[4] == 0x00 && frame[5] == 0x00,
              "pixel[1] == red (LZW code 1)");
        {
            uint8_t red[3] = {0xFF, 0x00, 0x00};
            uint8_t blue[3] = {0x00, 0x00, 0xFF};
            CHECK(gd_is_bgcolor(gif, red) == 1, "gd_is_bgcolor(red) == 1");
            CHECK(gd_is_bgcolor(gif, blue) == 0, "gd_is_bgcolor(blue) == 0");
        }
        ret = gd_get_frame(gif);
        CHECK(ret == 0, "2x1 trailer returns 0");
        gd_close_gif(gif);
    }

    /* ── GCE + NETSCAPE application extension ── */
    gif = gd_open_gif(write_gif("extensions.gif", GIF_EXT, sizeof(GIF_EXT)));
    CHECK(gif != NULL, "gd_open_gif(extensions) opens");
    if (gif) {
        CHECK(gif->loop_count == 0,
              "loop_count == 0 before first gd_get_frame (ext not yet parsed)");
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "extensions gd_get_frame returns 1");
        CHECK(gif->loop_count == 3, "NETSCAPE loop_count == 3 after frame parse");
        CHECK(gif->gce.delay == 10, "GCE delay == 10");
        CHECK(gif->gce.transparency == 0, "GCE transparency == 0");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0x00 &&
              frame[3] == 0xFF && frame[4] == 0x00 && frame[5] == 0x00,
              "extensions frame pixels == [black, red]");
        gd_close_gif(gif);
    }

    /* ── transparency: tindex pixel skipped, canvas bg kept ── */
    gif = gd_open_gif(write_gif("transparency.gif", GIF_TRANSP, sizeof(GIF_TRANSP)));
    CHECK(gif != NULL, "gd_open_gif(transparency) opens");
    if (gif) {
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "transparency gd_get_frame returns 1");
        CHECK(gif->gce.transparency == 1, "gce.transparency == 1");
        CHECK(gif->gce.tindex == 1, "gce.tindex == 1");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0xFF && frame[1] == 0xFF && frame[2] == 0xFF,
              "transp pixel[0] == white (code 0 rendered)");
        CHECK(frame[3] == 0xFF && frame[4] == 0xFF && frame[5] == 0xFF,
              "transp pixel[1] == white kept (tindex skipped)");
        gd_close_gif(gif);
    }

    /* ── local color table: frame palette overrides GCT ── */
    gif = gd_open_gif(write_gif("local_table.gif", GIF_LCT, sizeof(GIF_LCT)));
    CHECK(gif != NULL, "gd_open_gif(local color table) opens");
    if (gif) {
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "LCT gd_get_frame returns 1");
        CHECK(gif->palette != &gif->gct, "palette switched to local table");
        CHECK(gif->palette->size == 2, "LCT size == 2 entries");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0xFF,
              "LCT pixel[0] == blue (LCT[0])");
        CHECK(frame[3] == 0x00 && frame[4] == 0xFF && frame[5] == 0x00,
              "LCT pixel[1] == green (LCT[1])");
        gd_close_gif(gif);
    }

    /* ── two frames: default disposal accumulates on canvas ── */
    gif = gd_open_gif(write_gif("two_frames.gif", GIF_2FRAME, sizeof(GIF_2FRAME)));
    CHECK(gif != NULL, "gd_open_gif(two frames) opens");
    if (gif) {
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "frame 1 gd_get_frame returns 1");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0x00 &&
              frame[3] == 0xFF && frame[4] == 0x00 && frame[5] == 0x00,
              "frame 1 renders [black, red]");
        ret = gd_get_frame(gif);
        CHECK(ret == 1, "frame 2 gd_get_frame returns 1");
        memset(frame, 0xAA, sizeof(frame));
        gd_render_frame(gif, frame);
        CHECK(frame[0] == 0x00 && frame[1] == 0x00 && frame[2] == 0x00 &&
              frame[3] == 0x00 && frame[4] == 0x00 && frame[5] == 0x00,
              "frame 2: pixel[0] kept black, pixel[1] overwritten black");
        ret = gd_get_frame(gif);
        CHECK(ret == 0, "trailer after frame 2 returns 0");
        gd_close_gif(gif);
    }

    printf("gifdec consumer suite: %d checks, %d failures\n", checks, failures);
    return failures ? 1 : 0;
}
