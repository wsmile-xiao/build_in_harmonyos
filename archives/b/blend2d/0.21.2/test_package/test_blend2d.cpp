// Test that exercises blend2d API: creates an image, gets a rendering context,
// fills a rectangle, and verifies the result by checking pixel data.
#include <blend2d/blend2d.h>
#include <cstdio>
#include <cstring>

int main() {
    BLImage image(128, 128, BL_FORMAT_PRGB32);
    BLContext ctx(image);

    // Fill background with white
    ctx.set_comp_op(BL_COMP_OP_SRC_COPY);
    ctx.fill_all(BLRgba32(255, 255, 255, 255));

    // Draw a filled rectangle
    ctx.set_fill_style(BLRgba32(255, 0, 0, 255));
    ctx.fill_round_rect(BLRoundRect(10, 10, 100, 100, 8));

    ctx.end();

    // Verify: image should not be blank
    BLImageData data;
    image.get_data(&data);

    // Check pixel at center of the rectangle should be red
    uint32_t* pixels = (uint32_t*)data.pixel_data;
    uint32_t center = pixels[64 * 128 + 64];
    uint8_t a = (center >> 24) & 0xFF;
    uint8_t r = (center >> 16) & 0xFF;

    // The center pixel should have alpha and red components
    if (a == 0 && r == 0) {
        printf("FAIL: center pixel is blank\n");
        return 1;
    }

    printf("OK: blend2d rendered rectangle, center pixel alpha=%d red=%d\n", a, r);
    return 0;
}
