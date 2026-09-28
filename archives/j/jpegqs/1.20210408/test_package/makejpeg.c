#include <stdio.h>
#include <jpeglib.h>

/* Write a 16x16 baseline RGB JPEG with the reference encoder, i.e. the very
 * libjpeg copy jpegqs was linked against. Proves the dependency is usable and
 * gives jpegqs a real DQT/DHT/SOS stream to work on. */
int main(void) {
    struct jpeg_compress_struct cinfo;
    struct jpeg_error_mgr jerr;
    JSAMPROW row[1];
    unsigned char pixels[16 * 3];
    int x, y;
    FILE *fh = fopen("src.jpg", "wb");
    if (!fh) {
        perror("fopen");
        return 1;
    }
    cinfo.err = jpeg_std_error(&jerr);
    jpeg_create_compress(&cinfo);
    jpeg_stdio_dest(&cinfo, fh);
    cinfo.image_width = 16;
    cinfo.image_height = 16;
    cinfo.input_components = 3;
    cinfo.in_color_space = JCS_RGB;
    jpeg_set_defaults(&cinfo);
    jpeg_set_quality(&cinfo, 75, TRUE);
    jpeg_start_compress(&cinfo, TRUE);
    for (y = 0; y < 16; y++) {
        for (x = 0; x < 16; x++) {
            pixels[x * 3 + 0] = (unsigned char)(x * 16);
            pixels[x * 3 + 1] = (unsigned char)(y * 16);
            pixels[x * 3 + 2] = 128;
        }
        row[0] = pixels;
        jpeg_write_scanlines(&cinfo, row, 1);
    }
    jpeg_finish_compress(&cinfo);
    jpeg_destroy_compress(&cinfo);
    fclose(fh);
    printf("MAKED src.jpg\n");
    return 0;
}
