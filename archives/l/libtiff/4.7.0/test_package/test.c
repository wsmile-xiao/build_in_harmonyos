/*
 * libtiff 4.7.0 functional test — write + read back a TIFF file per codec.
 * Tests: TIFFOpen/TIFFClose/TIFFSetField/TIFFWriteScanline/TIFFReadScanline
 * Codecs covered: NONE, PACKBITS, DEFLATE(ZIP), ADOBE_DEFLATE, LZMA, ZSTD, LERC, WEBP
 * (each codec is backed by the corresponding conan dependency).
 */
#include <tiffio.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define W 32
#define H 32

static unsigned char orig[H][W];
static unsigned char readback[H][W];
static unsigned char orig_rgb[H][W * 3];
static unsigned char readback_rgb[H][W * 3];

static int write_tiff(const char *path, int compression, int spp, unsigned char *buf, int stride)
{
    TIFF *tif = TIFFOpen(path, "w");
    if (!tif) {
        fprintf(stderr, "TIFFOpen(w) %s failed (compression=%d)\n", path, compression);
        return 1;
    }
    TIFFSetField(tif, TIFFTAG_IMAGEWIDTH, W);
    TIFFSetField(tif, TIFFTAG_IMAGELENGTH, H);
    TIFFSetField(tif, TIFFTAG_BITSPERSAMPLE, 8);
    TIFFSetField(tif, TIFFTAG_SAMPLESPERPIXEL, spp);
    TIFFSetField(tif, TIFFTAG_ROWSPERSTRIP, H);
    TIFFSetField(tif, TIFFTAG_PHOTOMETRIC, spp == 1 ? PHOTOMETRIC_MINISBLACK : PHOTOMETRIC_RGB);
    TIFFSetField(tif, TIFFTAG_PLANARCONFIG, PLANARCONFIG_CONTIG);
    TIFFSetField(tif, TIFFTAG_COMPRESSION, compression);
    TIFFSetField(tif, TIFFTAG_SAMPLEFORMAT, SAMPLEFORMAT_UINT);
    if (compression == COMPRESSION_WEBP) {
        /* WEBP 默认有损（质量 75），roundtrip 像素比对须开无损 */
        TIFFSetField(tif, TIFFTAG_WEBP_LOSSLESS, 1);
    }
    for (int row = 0; row < H; row++) {
        if (TIFFWriteScanline(tif, buf + row * stride, row, 0) < 0) {
            fprintf(stderr, "TIFFWriteScanline failed at row %d (compression=%d)\n", row, compression);
            TIFFClose(tif);
            return 1;
        }
    }
    TIFFClose(tif);
    return 0;
}

static int read_tiff(const char *path, int compression, int spp, unsigned char *buf, int stride)
{
    TIFF *tif = TIFFOpen(path, "r");
    if (!tif) {
        fprintf(stderr, "TIFFOpen(r) %s failed (compression=%d)\n", path, compression);
        return 1;
    }
    uint32_t w = 0, h = 0;
    uint16_t bits = 0, rspp = 0, comp = 0;
    TIFFGetField(tif, TIFFTAG_IMAGEWIDTH, &w);
    TIFFGetField(tif, TIFFTAG_IMAGELENGTH, &h);
    TIFFGetField(tif, TIFFTAG_BITSPERSAMPLE, &bits);
    TIFFGetField(tif, TIFFTAG_SAMPLESPERPIXEL, &rspp);
    TIFFGetField(tif, TIFFTAG_COMPRESSION, &comp);
    if (w != W || h != H || bits != 8 || rspp != spp) {
        fprintf(stderr, "tag mismatch: %ux%u bits=%u spp=%u want spp=%d (compression=%d)\n",
                w, h, bits, rspp, spp, compression);
        TIFFClose(tif);
        return 1;
    }
    if (comp != (uint16_t)compression) {
        fprintf(stderr, "compression tag mismatch: got %u want %d\n", comp, compression);
        TIFFClose(tif);
        return 1;
    }
    memset(buf, 0, (size_t)H * stride);
    for (int row = 0; row < H; row++) {
        if (TIFFReadScanline(tif, buf + row * stride, row, 0) < 0) {
            fprintf(stderr, "TIFFReadScanline failed at row %d (compression=%d)\n", row, compression);
            TIFFClose(tif);
            return 1;
        }
    }
    TIFFClose(tif);
    return 0;
}

static int roundtrip(const char *name, int compression, int spp,
                     unsigned char *wbuf, unsigned char *rbuf, int stride, size_t cmpsz)
{
    char path[128];
    snprintf(path, sizeof(path), "test_%s.tif", name);
    if (write_tiff(path, compression, spp, wbuf, stride) != 0) {
        printf("codec %-16s: FAIL (write)\n", name);
        return 1;
    }
    if (read_tiff(path, compression, spp, rbuf, stride) != 0) {
        printf("codec %-16s: FAIL (read/verify)\n", name);
        return 1;
    }
    if (memcmp(wbuf, rbuf, cmpsz) != 0) {
        printf("codec %-16s: FAIL (pixel mismatch)\n", name);
        return 1;
    }
    printf("codec %-16s: OK\n", name);
    remove(path);
    return 0;
}

int main(void)
{
    printf("libtiff 4.7.0 codec roundtrip test\n");
    for (int i = 0; i < H; i++)
        for (int j = 0; j < W; j++) {
            orig[i][j] = (unsigned char)((i * 7 + j * 13) & 0xff);
            orig_rgb[i][j * 3 + 0] = (unsigned char)((i * 5 + j * 11) & 0xff);
            orig_rgb[i][j * 3 + 1] = (unsigned char)((i * 3 + j * 17) & 0xff);
            orig_rgb[i][j * 3 + 2] = (unsigned char)((i * 13 + j * 7) & 0xff);
        }

    int failures = 0;
    /* 灰度 1 波段编解码器 */
    failures += roundtrip("none",           COMPRESSION_NONE,           1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("packbits",       COMPRESSION_PACKBITS,       1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("deflate",        COMPRESSION_DEFLATE,        1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("adobe_deflate",  COMPRESSION_ADOBE_DEFLATE,  1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("lzma",           COMPRESSION_LZMA,           1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("zstd",           COMPRESSION_ZSTD,           1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    failures += roundtrip("lerc",           COMPRESSION_LERC,           1, (unsigned char *)orig,    (unsigned char *)readback,    W,     sizeof(orig));
    /* WEBP 要求 RGB(3)/RGBA(4) 波段 */
    failures += roundtrip("webp",           COMPRESSION_WEBP,           3, (unsigned char *)orig_rgb, (unsigned char *)readback_rgb, W * 3, sizeof(orig_rgb));
    if (failures) {
        fprintf(stderr, "FAILED: %d codec(s)\n", failures);
        return 1;
    }
    printf("all codec roundtrips OK\n");
    return 0;
}
