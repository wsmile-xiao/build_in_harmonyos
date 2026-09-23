/* libjpeg L1 consumer test: compress an RGB image to memory, decompress it
 * back and verify the round-trip result. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <jpeglib.h>

#define WIDTH 64
#define HEIGHT 48

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
    unsigned char *jpeg_buf = NULL;
    unsigned long jpeg_size = 0;
    JSAMPROW row;
    int y;

    printf("libjpeg version: %d\n", JPEG_LIB_VERSION);

    fill_image(rgb);

    /* Encode */
    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_mem_dest(&cinfo, &jpeg_buf, &jpeg_size);
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

    if (jpeg_buf == NULL || jpeg_size < 100) {
        fprintf(stderr, "compression produced no data\n");
        return 1;
    }
    if (jpeg_buf[0] != 0xFF || jpeg_buf[1] != 0xD8) {
        fprintf(stderr, "missing JPEG SOI marker\n");
        free(jpeg_buf);
        return 1;
    }
    printf("encoded %lu bytes\n", jpeg_size);

    /* Decode */
    dinfo.err = jpeg_std_error(&jerr);
    jpeg_create_decompress(&dinfo);
    jpeg_mem_src(&dinfo, jpeg_buf, jpeg_size);
    if (jpeg_read_header(&dinfo, TRUE) != JPEG_HEADER_OK) {
        fprintf(stderr, "jpeg_read_header failed\n");
        jpeg_destroy_decompress(&dinfo);
        free(jpeg_buf);
        return 1;
    }
    jpeg_start_decompress(&dinfo);
    if (dinfo.output_width != WIDTH || dinfo.output_height != HEIGHT ||
        dinfo.output_components != 3) {
        fprintf(stderr, "unexpected geometry: %ux%u x%d\n",
                (unsigned)dinfo.output_width, (unsigned)dinfo.output_height,
                dinfo.output_components);
        jpeg_destroy_decompress(&dinfo);
        free(jpeg_buf);
        return 1;
    }
    for (y = 0; (unsigned)y < dinfo.output_height; y++) {
        int i;
        row = decoded;
        if (jpeg_read_scanlines(&dinfo, &row, 1) != 1) {
            fprintf(stderr, "jpeg_read_scanlines failed at row %d\n", y);
            jpeg_destroy_decompress(&dinfo);
            free(jpeg_buf);
            return 1;
        }
        /* Lossy codec: allow a small deviation from the source pixels. */
        for (i = 0; i < WIDTH * 3; i++) {
            int diff = abs((int)decoded[i] - (int)rgb[y * WIDTH * 3 + i]);
            if (diff > 16) {
                fprintf(stderr, "pixel mismatch at row %d byte %d: %d vs %d\n",
                        y, i, decoded[i], rgb[y * WIDTH * 3 + i]);
                jpeg_destroy_decompress(&dinfo);
                free(jpeg_buf);
                return 1;
            }
        }
    }
    jpeg_finish_decompress(&dinfo);
    jpeg_destroy_decompress(&dinfo);
    free(jpeg_buf);

    printf("libjpeg test: OK\n");
    return 0;
}
