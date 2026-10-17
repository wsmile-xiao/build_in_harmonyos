/* libjpeg6b L1 consumer test: compress an RGB image through the stdio
 * backend (jpeg-6b predates jpeg_mem_src/jpeg_mem_dest), read it back and
 * verify the round-trip result.
 *
 * NOTE: do not include stdbool.h here. jmorecfg.h of jpeg-6b does
 * `typedef int boolean;` and a C99 bool redefinition would break the build.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <jpeglib.h>

#define WIDTH 64
#define HEIGHT 48
#define OUT_NAME "test_libjpeg6b_out.jpg"

static void fill_image(unsigned char *rgb) {
    int x, y;
    for (y = 0; y < HEIGHT; y++) {
        for (x = 0; x < WIDTH; x++) {
            unsigned char *p = rgb + (y * WIDTH + x) * 3;
            p[0] = (unsigned char)(x * 4);
            p[1] = (unsigned char)(y * 5);
            p[2] = 128;
        }
    }
}

int main(void) {
    struct jpeg_compress_struct cinfo;
    struct jpeg_decompress_struct dinfo;
    struct jpeg_error_mgr jerr;
    unsigned char rgb[WIDTH * HEIGHT * 3];
    unsigned char decoded[WIDTH * 3];
    unsigned char soi[2];
    JSAMPROW row;
    FILE *f;
    long fsize = 0;
    int y;

    printf("libjpeg6b version: %d\n", JPEG_LIB_VERSION);

    fill_image(rgb);

    /* Encode to a file through the stdio destination. */
    f = fopen(OUT_NAME, "wb");
    if (f == NULL) {
        fprintf(stderr, "cannot open %s for writing\n", OUT_NAME);
        return 1;
    }
    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_stdio_dest(&cinfo, f);
    cinfo.image_width = WIDTH;
    cinfo.image_height = HEIGHT;
    cinfo.input_components = 3;
    cinfo.in_color_space = JCS_RGB;
    jpeg_set_defaults(&cinfo);
    jpeg_set_quality(&cinfo, 90, TRUE);
    jpeg_start_compress(&cinfo, TRUE);
    while (cinfo.next_scanline < cinfo.image_height) {
        row = rgb + cinfo.next_scanline * WIDTH * 3;
        jpeg_write_scanlines(&cinfo, &row, 1);
    }
    jpeg_finish_compress(&cinfo);
    jpeg_destroy_compress(&cinfo);
    if (ferror(f) || fclose(f) != 0) {
        fprintf(stderr, "compression write failed\n");
        return 1;
    }

    /* Check the file is a plausible JPEG stream. */
    f = fopen(OUT_NAME, "rb");
    if (f == NULL) {
        fprintf(stderr, "cannot reopen %s\n", OUT_NAME);
        return 1;
    }
    if (fseek(f, 0, SEEK_END) != 0 || (fsize = ftell(f)) < 100L) {
        fprintf(stderr, "suspiciously small output: %ld bytes\n", fsize);
        fclose(f);
        return 1;
    }
    rewind(f);
    if (fread(soi, 1, 2, f) != 2 || soi[0] != 0xFF || soi[1] != 0xD8) {
        fprintf(stderr, "missing JPEG SOI marker\n");
        fclose(f);
        return 1;
    }
    printf("encoded %ld bytes\n", fsize);

    /* Rewind past the SOI bytes we just consumed so the decoder sees the
     * whole stream from offset 0. */
    rewind(f);

    /* Decode back through the stdio source. */
    dinfo.err = jpeg_std_error(&jerr);
    jpeg_create_decompress(&dinfo);
    jpeg_stdio_src(&dinfo, f);
    if (jpeg_read_header(&dinfo, TRUE) != JPEG_HEADER_OK) {
        fprintf(stderr, "jpeg_read_header failed\n");
        jpeg_destroy_decompress(&dinfo);
        fclose(f);
        return 1;
    }
    jpeg_start_decompress(&dinfo);
    if (dinfo.output_width != WIDTH || dinfo.output_height != HEIGHT ||
        dinfo.output_components != 3) {
        fprintf(stderr, "unexpected geometry: %ux%u x%d\n",
                (unsigned)dinfo.output_width, (unsigned)dinfo.output_height,
                dinfo.output_components);
        jpeg_destroy_decompress(&dinfo);
        fclose(f);
        return 1;
    }
    for (y = 0; (int)dinfo.output_height > y; y++) {
        int i;
        row = decoded;
        if (jpeg_read_scanlines(&dinfo, &row, 1) != 1) {
            fprintf(stderr, "jpeg_read_scanlines failed at row %d\n", y);
            jpeg_destroy_decompress(&dinfo);
            fclose(f);
            return 1;
        }
        /* Lossy codec: allow a small deviation from the source pixels. */
        for (i = 0; i < WIDTH * 3; i++) {
            int diff = abs((int)decoded[i] - (int)rgb[y * WIDTH * 3 + i]);
            if (diff > 16) {
                fprintf(stderr, "pixel mismatch at row %d byte %d: %d vs %d\n",
                        y, i, decoded[i], rgb[y * WIDTH * 3 + i]);
                jpeg_destroy_decompress(&dinfo);
                fclose(f);
                return 1;
            }
        }
    }
    jpeg_finish_decompress(&dinfo);
    jpeg_destroy_decompress(&dinfo);
    fclose(f);
    remove(OUT_NAME);

    printf("libjpeg6b test: OK\n");
    return 0;
}
