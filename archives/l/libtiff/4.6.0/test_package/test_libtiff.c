/*
 * test_libtiff.c — Substantive test for libtiff 4.6.0
 *
 * Creates a minimal TIFF file, writes a scanline, closes,
 * reopens, reads back dimensions, and verifies correctness.
 */
#include <tiffio.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    const char *version = TIFFGetVersion();
    if (!version || !version[0]) {
        fprintf(stderr, "FAIL: TIFFGetVersion returned empty\n");
        return 1;
    }

    /* Determine temp directory (E002: /tmp may be read-only on OHOS) */
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir || !tmpdir[0])
        tmpdir = getenv("TEMP");
    if (!tmpdir || !tmpdir[0])
        tmpdir = ".";
    char path[1024];
    snprintf(path, sizeof(path), "%s/test_libtiff_out.tiff", tmpdir);

    /* Create a 4x4 8-bit grayscale TIFF */
    TIFF *tif = TIFFOpen(path, "w");
    if (!tif) {
        fprintf(stderr, "FAIL: TIFFOpen(%s, \"w\") failed\n", path);
        return 1;
    }

    TIFFSetField(tif, TIFFTAG_IMAGEWIDTH, 4);
    TIFFSetField(tif, TIFFTAG_IMAGELENGTH, 4);
    TIFFSetField(tif, TIFFTAG_BITSPERSAMPLE, 8);
    TIFFSetField(tif, TIFFTAG_SAMPLESPERPIXEL, 1);
    TIFFSetField(tif, TIFFTAG_ROWSPERSTRIP, 4);
    TIFFSetField(tif, TIFFTAG_PHOTOMETRIC, PHOTOMETRIC_MINISBLACK);

    unsigned char row[4];
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++)
            row[j] = (unsigned char)(i * 4 + j);
        if (TIFFWriteScanline(tif, row, i, 0) < 0) {
            fprintf(stderr, "FAIL: TIFFWriteScanline failed at row %d\n", i);
            TIFFClose(tif);
            return 1;
        }
    }
    TIFFClose(tif);

    /* Reopen and verify */
    tif = TIFFOpen(path, "r");
    if (!tif) {
        fprintf(stderr, "FAIL: Cannot reopen TIFF file for reading\n");
        return 1;
    }

    uint32_t w = 0, h = 0;
    TIFFGetField(tif, TIFFTAG_IMAGEWIDTH, &w);
    TIFFGetField(tif, TIFFTAG_IMAGELENGTH, &h);
    TIFFClose(tif);

    if (w != 4 || h != 4) {
        fprintf(stderr, "FAIL: Expected 4x4, got %ux%u\n", w, h);
        return 1;
    }

    remove(path);
    printf("test libtiff 4.6.0: OK (version=%s)\n", version);
    return 0;
}
