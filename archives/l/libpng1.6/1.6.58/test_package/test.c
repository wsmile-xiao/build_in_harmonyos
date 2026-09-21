#include <png.h>
#include <stdio.h>
#include <string.h>

static int check_version(void)
{
    const png_uint_32 runtime_version = png_access_version_number();
    const char *version_text = png_get_libpng_ver(NULL);

    if (runtime_version != PNG_LIBPNG_VER) {
        fprintf(stderr, "version mismatch: runtime=%lu headers=%d\n",
                (unsigned long)runtime_version, PNG_LIBPNG_VER);
        return 1;
    }
    if (version_text == NULL || version_text[0] == '\0' ||
        strstr(version_text, "1.6.58") == NULL) {
        fprintf(stderr, "unexpected version text: %s\n",
                version_text ? version_text : "(null)");
        return 1;
    }
    printf("[PASS] version: runtime=%lu header=%d text=%s\n",
           (unsigned long)runtime_version, PNG_LIBPNG_VER, version_text);
    return 0;
}

static int check_read_struct(void)
{
    png_structp png_ptr =
        png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    png_infop info_ptr;

    if (png_ptr == NULL) {
        fprintf(stderr, "png_create_read_struct failed\n");
        return 1;
    }
    info_ptr = png_create_info_struct(png_ptr);
    if (info_ptr == NULL) {
        fprintf(stderr, "png_create_info_struct failed\n");
        png_destroy_read_struct(&png_ptr, NULL, NULL);
        return 1;
    }
    png_destroy_read_struct(&png_ptr, &info_ptr, NULL);
    if (png_ptr != NULL || info_ptr != NULL) {
        fprintf(stderr, "png_destroy_read_struct did not clear pointers\n");
        return 1;
    }
    printf("[PASS] read struct create/destroy\n");
    return 0;
}

static int check_write_struct(void)
{
    png_structp png_ptr =
        png_create_write_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
    png_infop info_ptr;

    if (png_ptr == NULL) {
        fprintf(stderr, "png_create_write_struct failed\n");
        return 1;
    }
    info_ptr = png_create_info_struct(png_ptr);
    if (info_ptr == NULL) {
        fprintf(stderr, "png_create_info_struct failed\n");
        png_destroy_write_struct(&png_ptr, NULL);
        return 1;
    }
    png_set_IHDR(png_ptr, info_ptr, 1, 1, 8, PNG_COLOR_TYPE_GRAY,
                 PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT,
                 PNG_FILTER_TYPE_DEFAULT);
    if (png_get_image_width(png_ptr, info_ptr) != 1 ||
        png_get_image_height(png_ptr, info_ptr) != 1) {
        fprintf(stderr, "IHDR round-trip through info struct failed\n");
        png_destroy_write_struct(&png_ptr, &info_ptr);
        return 1;
    }
    png_destroy_write_struct(&png_ptr, &info_ptr);
    printf("[PASS] write struct create/IHDR/destroy\n");
    return 0;
}

int main(void)
{
    int failures = 0;

    failures += check_version();
    failures += check_read_struct();
    failures += check_write_struct();
    printf("%d/3 checks passed\n", 3 - failures);
    return failures ? 1 : 0;
}
