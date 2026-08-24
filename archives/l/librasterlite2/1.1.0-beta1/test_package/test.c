#include <rasterlite2/rasterlite2.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int check(int condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void) {
    int passed = 0;
    rl2PixelPtr pixel = NULL;
    rl2PalettePtr palette = NULL;
    rl2SectionPtr section = NULL;
    rl2RasterPtr raster = NULL;
    unsigned char sample = 0;
    unsigned char sample_type = 0;
    unsigned char pixel_type = 0;
    unsigned char bands = 0;
    unsigned int width = 0;
    unsigned int height = 0;
    unsigned char *buffer = NULL;

    passed += check(strcmp(rl2_version(), "1.1.0-beta1") == 0, "version");
    passed += check(rl2_target_cpu() != NULL, "target cpu");
    passed += check(rl2_is_supported_codec(RL2_COMPRESSION_NONE) == RL2_TRUE,
                    "uncompressed codec");
    passed += check(rl2_is_supported_codec(RL2_COMPRESSION_PNG) == RL2_TRUE,
                    "PNG codec");

    pixel = rl2_create_pixel(RL2_SAMPLE_UINT8, RL2_PIXEL_RGB, 3);
    passed += check(pixel != NULL, "create RGB pixel");
    passed += check(rl2_get_pixel_type(pixel, &sample_type, &pixel_type, &bands) == RL2_OK,
                    "read pixel type");
    passed += check(sample_type == RL2_SAMPLE_UINT8 && pixel_type == RL2_PIXEL_RGB && bands == 3,
                    "pixel metadata");
    passed += check(rl2_set_pixel_sample_uint8(pixel, 0, 17) == RL2_OK,
                    "write pixel sample");
    passed += check(rl2_get_pixel_sample_uint8(pixel, 0, &sample) == RL2_OK && sample == 17,
                    "read pixel sample");
    rl2_destroy_pixel(pixel);

    palette = rl2_create_palette(2);
    passed += check(palette != NULL, "create palette");
    passed += check(rl2_set_palette_hexrgb(palette, 0, "#102030") == RL2_OK,
                    "set palette color");
    rl2_destroy_palette(palette);

    buffer = calloc(16 * 16, 1);
    raster = rl2_create_raster(16, 16, RL2_SAMPLE_UINT8, RL2_PIXEL_GRAYSCALE, 1,
                                buffer, 16 * 16, NULL, NULL, 0, NULL);
    passed += check(raster != NULL, "create raster");
    if (raster == NULL) {
        free(buffer);
    }
    if (raster != NULL) {
        passed += check(rl2_get_raster_size(raster, &width, &height) == RL2_OK &&
                        width == 16 && height == 16, "raster dimensions");
    }

    section = rl2_create_section("consumer", RL2_COMPRESSION_NONE, 256, 256, raster);
    passed += check(section != NULL, "create section");
    if (section != NULL) {
        raster = NULL;
        rl2_destroy_section(section);
    }
    if (raster != NULL) {
        rl2_destroy_raster(raster);
    }

    if (passed != 14) {
        fprintf(stderr, "LIBRASTERLITE2_CONSUMER_ASSERTIONS=%d/14\n", passed);
        return 1;
    }
    printf("LIBRASTERLITE2_CONSUMER_ASSERTIONS=14/14\n");
    return 0;
}
