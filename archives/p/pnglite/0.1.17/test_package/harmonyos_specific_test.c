#include <pnglite.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__OHOS__)
#error "This test must be compiled by the HarmonyOS/OpenHarmony toolchain"
#endif

#if !defined(__aarch64__)
#error "The HarmonyOS PC target for this migration must be AArch64"
#endif

typedef struct {
    unsigned char data[256];
    size_t size;
} ohos_buffer_t;

static unsigned ohos_write(void *input, size_t size, size_t count, void *opaque)
{
    ohos_buffer_t *buffer = (ohos_buffer_t *)opaque;
    size_t bytes = size * count;

    if (buffer->size + bytes > sizeof(buffer->data)) {
        return 0;
    }
    memcpy(buffer->data + buffer->size, input, bytes);
    buffer->size += bytes;
    return (unsigned)count;
}

int main(void)
{
    static const unsigned char png_signature[8] = {
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a
    };
    unsigned char pixel = 0x7f;
    ohos_buffer_t output = {{0}, 0};
    png_t png = {0};

    if (sizeof(void *) != 8) {
        fprintf(stderr, "FAIL: HarmonyOS AArch64 pointer size is %zu\n", sizeof(void *));
        return EXIT_FAILURE;
    }
    if (png_init(NULL, NULL) != PNG_NO_ERROR) {
        fprintf(stderr, "FAIL: png_init on HarmonyOS\n");
        return EXIT_FAILURE;
    }
    if (png_open_write(&png, ohos_write, &output) != PNG_NO_ERROR) {
        fprintf(stderr, "FAIL: callback IO on HarmonyOS\n");
        return EXIT_FAILURE;
    }
    if (png_set_data(&png, 1, 1, 8, PNG_GREYSCALE, &pixel) != PNG_NO_ERROR) {
        fprintf(stderr, "FAIL: zlib-backed encoding on HarmonyOS\n");
        return EXIT_FAILURE;
    }
    if (output.size <= sizeof(png_signature) ||
        memcmp(output.data, png_signature, sizeof(png_signature)) != 0) {
        fprintf(stderr, "FAIL: encoded PNG signature on HarmonyOS\n");
        return EXIT_FAILURE;
    }

    printf("HarmonyOS AArch64 pnglite encoding: 5 assertions passed\n");
    return EXIT_SUCCESS;
}
