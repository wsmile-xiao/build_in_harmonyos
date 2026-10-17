#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <jpeglib.h>

#if !defined(__OHOS__) || !defined(__aarch64__)
#error This end-to-end test must be built for HarmonyOS AArch64.
#endif

int main(void)
{
    enum { width = 16, height = 16, channels = 3 };
    unsigned char row[width * channels];
    unsigned char decoded[width * channels];
    struct jpeg_compress_struct encoder;
    struct jpeg_decompress_struct decoder;
    struct jpeg_error_mgr encode_error, decode_error;
    JSAMPROW row_pointer[1] = {row};
    JSAMPROW decoded_pointer[1] = {decoded};
    char filename[512];
    const char *home = getenv("HOME");
    FILE *stream;

    if (!home || strncmp(home, "/storage/Users/", 15) != 0 ||
        snprintf(filename, sizeof(filename), "%s/libjpeg turbo 鸿蒙-%ld.jpg",
                 home, (long)getpid()) >= (int)sizeof(filename)) {
        fprintf(stderr, "Expected a writable HarmonyOS user storage path\n");
        return 1;
    }
    for (int x = 0; x < width; ++x) {
        row[x * channels] = 28;
        row[x * channels + 1] = 132;
        row[x * channels + 2] = 224;
    }
    stream = fopen(filename, "wb");
    if (!stream) { perror("open JPEG output"); return 1; }
    encoder.err = jpeg_std_error(&encode_error);
    jpeg_create_compress(&encoder);
    jpeg_stdio_dest(&encoder, stream);
    encoder.image_width = width;
    encoder.image_height = height;
    encoder.input_components = channels;
    encoder.in_color_space = JCS_RGB;
    jpeg_set_defaults(&encoder);
    jpeg_set_quality(&encoder, 95, TRUE);
    jpeg_start_compress(&encoder, TRUE);
    while (encoder.next_scanline < encoder.image_height)
        jpeg_write_scanlines(&encoder, row_pointer, 1);
    jpeg_finish_compress(&encoder);
    jpeg_destroy_compress(&encoder);
    fclose(stream);

    stream = fopen(filename, "rb");
    if (!stream) { perror("open JPEG input"); unlink(filename); return 1; }
    decoder.err = jpeg_std_error(&decode_error);
    jpeg_create_decompress(&decoder);
    jpeg_stdio_src(&decoder, stream);
    jpeg_read_header(&decoder, TRUE);
    jpeg_start_decompress(&decoder);
    if (decoder.output_width != width || decoder.output_height != height ||
        decoder.output_components != channels) {
        fprintf(stderr, "JPEG dimensions or RGB components changed\n");
        jpeg_destroy_decompress(&decoder);
        fclose(stream);
        unlink(filename);
        return 1;
    }
    while (decoder.output_scanline < decoder.output_height) {
        jpeg_read_scanlines(&decoder, decoded_pointer, 1);
        for (int i = 0; i < width * channels; ++i) {
            int delta = (int)row[i] - (int)decoded[i];
            if (delta < -12 || delta > 12) {
                fprintf(stderr, "JPEG pixel mismatch at component %d\n", i);
                jpeg_destroy_decompress(&decoder);
                fclose(stream);
                unlink(filename);
                return 1;
            }
        }
    }
    jpeg_finish_decompress(&decoder);
    jpeg_destroy_decompress(&decoder);
    fclose(stream);
    unlink(filename);
    puts("HarmonyOS user-storage JPEG encode/file/decode round trip passed");
    return 0;
}
