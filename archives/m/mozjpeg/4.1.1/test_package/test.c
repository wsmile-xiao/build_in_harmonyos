#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

#include <jpeglib.h>

static int encode_one_pixel(unsigned char **jpeg_data, unsigned long *jpeg_size)
{
    struct jpeg_compress_struct compressor;
    struct jpeg_error_mgr error;
    JSAMPROW row;
    unsigned char pixel[3] = { 220, 30, 40 };

    compressor.err = jpeg_std_error(&error);
    jpeg_create_compress(&compressor);
    jpeg_mem_dest(&compressor, jpeg_data, jpeg_size);
    compressor.image_width = 1;
    compressor.image_height = 1;
    compressor.input_components = 3;
    compressor.in_color_space = JCS_RGB;
    jpeg_set_defaults(&compressor);
    jpeg_start_compress(&compressor, TRUE);
    row = pixel;
    if (jpeg_write_scanlines(&compressor, &row, 1) != 1) {
        jpeg_destroy_compress(&compressor);
        free(*jpeg_data);
        *jpeg_data = NULL;
        *jpeg_size = 0;
        return 0;
    }
    jpeg_finish_compress(&compressor);
    jpeg_destroy_compress(&compressor);
    return 1;
}

static int decode_one_pixel(const unsigned char *jpeg_data, unsigned long jpeg_size)
{
    struct jpeg_decompress_struct decompressor;
    struct jpeg_error_mgr error;
    JSAMPARRAY row;
    int ok;

    decompressor.err = jpeg_std_error(&error);
    jpeg_create_decompress(&decompressor);
    jpeg_mem_src(&decompressor, jpeg_data, jpeg_size);
    if (jpeg_read_header(&decompressor, TRUE) != JPEG_HEADER_OK ||
        decompressor.image_width != 1 || decompressor.image_height != 1) {
        jpeg_destroy_decompress(&decompressor);
        return 0;
    }
    if (!jpeg_start_decompress(&decompressor)) {
        jpeg_destroy_decompress(&decompressor);
        return 0;
    }
    row = (*decompressor.mem->alloc_sarray)(
        (j_common_ptr)&decompressor, JPOOL_IMAGE,
        decompressor.output_width * decompressor.output_components, 1);
    ok = jpeg_read_scanlines(&decompressor, row, 1) == 1;
    ok = ok && jpeg_finish_decompress(&decompressor);
    jpeg_destroy_decompress(&decompressor);
    return ok;
}

int main(void)
{
    unsigned char *jpeg_data = NULL;
    unsigned long jpeg_size = 0;
    int ok = encode_one_pixel(&jpeg_data, &jpeg_size) &&
             jpeg_size > 2 && jpeg_data[0] == 0xff && jpeg_data[1] == 0xd8 &&
             decode_one_pixel(jpeg_data, jpeg_size);

    free(jpeg_data);
    if (!ok) {
        fputs("mozjpeg functional checks failed\n", stderr);
        return EXIT_FAILURE;
    }
    puts("mozjpeg functional checks passed: 5");
    return EXIT_SUCCESS;
}
