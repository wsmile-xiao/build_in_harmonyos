/*
 * openslide 4.0.1 consumer smoke test (L1).
 *
 * Generates a minimal tiled RGB TIFF slide (256x256, 128x128 tiles, no
 * compression) in a temp file and opens it through the OpenSlide public API.
 * A tiled TIFF is what OpenSlide's generic-tiff vendor requires
 * (src/openslide-vendor-generic-tiff.c: "ensure TIFF is tiled"); it is
 * detected as vendor "generic-tiff".
 *
 * Verified via the OpenSlide public API:
 *   - openslide_open() non-NULL, no error string
 *   - level count >= 1
 *   - level 0 dimensions == 256x256
 *   - read_region() succeeds and returns nonzero content
 *   - openslide_close() completes
 *
 * Returns 0 on success, non-zero on any failed assertion.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <openslide/openslide.h>

#define IMG_W 256
#define IMG_H 256
#define TILE_W 128
#define TILE_H 128
#define SPP 3
#define TILES_X (IMG_W / TILE_W)
#define TILES_Y (IMG_H / TILE_H)
#define NTILES (TILES_X * TILES_Y)
#define TILE_BYTES (TILE_W * TILE_H * SPP)

/* IFD: 2 header bytes + 15 entries * 12 + 4 next-IFD bytes; extra payload
 * (SHORT/RATIONAL/LONG arrays) follows, then the tile data. */
#define IFD_OFFSET 8u
#define IFD_NENTRIES 15u
#define EXTRA_OFFSET (IFD_OFFSET + 2u + IFD_NENTRIES * 12u + 4u)
#define BPS_OFFSET EXTRA_OFFSET                    /* 3 x SHORT (8,8,8) */
#define XRES_OFFSET (BPS_OFFSET + 6u)              /* RATIONAL          */
#define YRES_OFFSET (XRES_OFFSET + 8u)             /* RATIONAL          */
#define SFMT_OFFSET (YRES_OFFSET + 8u)             /* 3 x SHORT (1,1,1) */
#define OFFS_OFFSET (SFMT_OFFSET + 6u)             /* NTILES x LONG     */
#define CNTS_OFFSET (OFFS_OFFSET + 4u * NTILES)    /* NTILES x LONG     */
#define PIX_OFFSET (CNTS_OFFSET + 4u * NTILES)
#define FILE_SIZE (PIX_OFFSET + (size_t)NTILES * TILE_BYTES)

static void put16(unsigned char *p, unsigned int v) {
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
}
static void put32(unsigned char *p, unsigned int v) {
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
    p[2] = (unsigned char)((v >> 16) & 0xff);
    p[3] = (unsigned char)((v >> 24) & 0xff);
}

static int write_tiled_tiff(const char *path) {
    unsigned char *buf = (unsigned char *)calloc(1, FILE_SIZE);
    if (!buf)
        return -1;

    /* header: II + 42 + IFD offset */
    buf[0] = 'I'; buf[1] = 'I';
    buf[2] = 42;  buf[3] = 0;
    put32(buf + 4, IFD_OFFSET);

    put16(buf + IFD_OFFSET, IFD_NENTRIES);
    unsigned long entry = IFD_OFFSET + 2u;

#define ENTRY_U16(tagv, typev, val) do { \
        put16(buf + entry, (tagv)); put16(buf + entry + 2, (typev)); \
        put32(buf + entry + 4, 1); put16(buf + entry + 8, (unsigned int)(val)); \
        put16(buf + entry + 10, 0); entry += 12; \
    } while (0)
#define ENTRY_U32(tagv, typev, val) do { \
        put16(buf + entry, (tagv)); put16(buf + entry + 2, (typev)); \
        put32(buf + entry + 4, 1); put32(buf + entry + 8, (unsigned int)(val)); \
        entry += 12; \
    } while (0)
#define ENTRY_OFF(tagv, typev, countv, off) do { \
        put16(buf + entry, (tagv)); put16(buf + entry + 2, (typev)); \
        put32(buf + entry + 4, (unsigned int)(countv)); \
        put32(buf + entry + 8, (unsigned int)(off)); \
        entry += 12; \
    } while (0)

    ENTRY_U32(256, 4, IMG_W);                    /* ImageWidth      LONG  */
    ENTRY_U32(257, 4, IMG_H);                    /* ImageLength     LONG  */
    ENTRY_OFF(258, 3, SPP, BPS_OFFSET);          /* BitsPerSample   SHORT */
    ENTRY_U16(259, 3, 1);                        /* Compression     none  */
    ENTRY_U16(262, 3, 2);                        /* Photometric     RGB   */
    ENTRY_U16(277, 3, SPP);                      /* SamplesPerPixel SHORT */
    ENTRY_OFF(282, 5, 1, XRES_OFFSET);           /* XResolution     RATIONAL */
    ENTRY_OFF(283, 5, 1, YRES_OFFSET);           /* YResolution     RATIONAL */
    ENTRY_U16(284, 3, 1);                        /* PlanarConfig    CHUNK */
    ENTRY_U16(296, 3, 2);                        /* ResolutionUnit  inch  */
    ENTRY_U32(322, 4, TILE_W);                   /* TileWidth       LONG  */
    ENTRY_U32(323, 4, TILE_H);                   /* TileLength      LONG  */
    ENTRY_OFF(324, 4, NTILES, OFFS_OFFSET);      /* TileOffsets     LONG  */
    ENTRY_OFF(325, 4, NTILES, CNTS_OFFSET);      /* TileByteCounts  LONG  */
    ENTRY_OFF(339, 3, SPP, SFMT_OFFSET);         /* SampleFormat    SHORT */

    put32(buf + entry, 0);                       /* next IFD = none */

    /* extra payloads */
    put16(buf + BPS_OFFSET + 0, 8);
    put16(buf + BPS_OFFSET + 2, 8);
    put16(buf + BPS_OFFSET + 4, 8);
    put32(buf + XRES_OFFSET + 0, 72); put32(buf + XRES_OFFSET + 4, 1);
    put32(buf + YRES_OFFSET + 0, 72); put32(buf + YRES_OFFSET + 4, 1);
    put16(buf + SFMT_OFFSET + 0, 1);
    put16(buf + SFMT_OFFSET + 2, 1);
    put16(buf + SFMT_OFFSET + 4, 1);

    int tile = 0;
    for (int ty = 0; ty < TILES_Y; ty++) {
        for (int tx = 0; tx < TILES_X; tx++, tile++) {
            put32(buf + OFFS_OFFSET + 4u * (unsigned)tile,
                  (unsigned)(PIX_OFFSET + (unsigned)tile * TILE_BYTES));
            put32(buf + CNTS_OFFSET + 4u * (unsigned)tile, TILE_BYTES);

            unsigned char *tilebuf = buf + PIX_OFFSET + (size_t)tile * TILE_BYTES;
            for (int y = 0; y < TILE_H; y++) {
                int gy = ty * TILE_H + y;
                for (int x = 0; x < TILE_W; x++) {
                    int gx = tx * TILE_W + x;
                    unsigned char *px = tilebuf + ((size_t)y * TILE_W + (unsigned)x) * SPP;
                    px[0] = (unsigned char)(gx & 0xFF);
                    px[1] = (unsigned char)(gy & 0xFF);
                    px[2] = 0x80;
                }
            }
        }
    }

    FILE *f = fopen(path, "wb");
    if (!f) { free(buf); return -1; }
    size_t written = fwrite(buf, 1, FILE_SIZE, f);
    fclose(f);
    free(buf);
    return (written == FILE_SIZE) ? 0 : -1;
}

static int failures = 0;
#define CHECK(cond, msg) do { \
        if (cond) { printf("PASS: %s\n", msg); } \
        else { printf("FAIL: %s\n", msg); failures++; } \
    } while (0)

int main(void) {
    const char *path = "synthetic-generic-tiff.tif";
    if (write_tiled_tiff(path) != 0) {
        printf("FAIL: cannot write synthetic tiled TIFF\n");
        return 2;
    }

    const char *vendor = openslide_detect_vendor(path);
    printf("INFO: detected vendor: %s\n", vendor ? vendor : "(none)");
    CHECK(vendor != NULL, "openslide_detect_vendor() recognized the slide");

    openslide_t *osr = openslide_open(path);
    CHECK(osr != NULL, "openslide_open() returned non-NULL");
    if (osr == NULL) {
        printf("INFO: open failed - tiled generic TIFF rejected by this build\n");
        remove(path);
        return 3;
    }
    CHECK(openslide_get_error(osr) == NULL, "openslide_get_error() is clean");

    int32_t level_count = openslide_get_level_count(osr);
    CHECK(level_count >= 1, "level_count >= 1");

    int64_t w = 0, h = 0;
    openslide_get_level_dimensions(osr, 0, &w, &h);
    CHECK(w == IMG_W && h == IMG_H, "level 0 dimensions == 256x256");

    uint32_t *buf = (uint32_t *)malloc((size_t)(IMG_W * IMG_H) * sizeof(uint32_t));
    if (!buf) {
        openslide_close(osr);
        printf("FAIL: malloc\n");
        return 4;
    }
    memset(buf, 0, (size_t)(IMG_W * IMG_H) * sizeof(uint32_t));
    openslide_read_region(osr, buf, 0, 0, 0, IMG_W, IMG_H);
    CHECK(openslide_get_error(osr) == NULL, "read_region() returned clean status");

    int nonzero = 0;
    for (size_t i = 0; i < (size_t)(IMG_W * IMG_H); i++) {
        if (buf[i] != 0) { nonzero = 1; break; }
    }
    CHECK(nonzero != 0, "read_region() produced nonzero pixels");

    free(buf);
    openslide_close(osr);
    CHECK(1, "openslide_close() completed");
    remove(path);

    if (failures == 0) {
        printf("openslide smoke test: ALL PASSED\n");
        return 0;
    }
    printf("openslide smoke test: %d FAILURE(S)\n", failures);
    return 1;
}
