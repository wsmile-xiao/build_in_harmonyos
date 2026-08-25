#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include <nsgif.h>

static int checks = 0;

#define CHECK(expr)                                                   \
    do {                                                              \
        if (!(expr)) {                                                \
            fprintf(stderr, "CHECK failed: %s\n", #expr);             \
            return EXIT_FAILURE;                                      \
        }                                                             \
        checks++;                                                     \
    } while (0)
static nsgif_bitmap_t *bitmap_create(int width, int height)
{
    return calloc((size_t)width * (size_t)height, 4);
}

static void bitmap_destroy(nsgif_bitmap_t *bitmap)
{
    free(bitmap);
}

static uint8_t *bitmap_get_buffer(nsgif_bitmap_t *bitmap)
{
    return (uint8_t *)bitmap;
}

int main(void)
{
    static const uint8_t gif_data[] = {
        0x47, 0x49, 0x46, 0x38, 0x39, 0x61,
        0x01, 0x00, 0x01, 0x00,
        0x80, 0x00, 0x00,
        0x00, 0x00, 0x00,
        0xff, 0xff, 0xff,
        0x21, 0xf9, 0x04, 0x01,
        0x00, 0x00, 0x00, 0x00,
        0x2c,
        0x00, 0x00, 0x00, 0x00,
        0x01, 0x00, 0x01, 0x00,
        0x00,
        0x02, 0x02, 0x44, 0x01, 0x00,
        0x3b
    };

    const nsgif_bitmap_cb_vt bitmap_callbacks = {
        .create = bitmap_create,
        .destroy = bitmap_destroy,
        .get_buffer = bitmap_get_buffer,
    };

    nsgif_t *gif = NULL;
    const nsgif_info_t *info;
    nsgif_bitmap_t *bitmap = NULL;
    nsgif_rect_t area;
    uint32_t delay_cs = 0;
    uint32_t frame = 0;
    nsgif_error err;

    err = nsgif_create(
        &bitmap_callbacks,
        NSGIF_BITMAP_FMT_R8G8B8A8,
        &gif
    );
    CHECK(err == NSGIF_OK);

    err = nsgif_data_scan(gif, sizeof(gif_data), gif_data);
    CHECK(err == NSGIF_OK);

    nsgif_data_complete(gif);

    info = nsgif_get_info(gif);
    CHECK(info != NULL);
    CHECK(info->width == 1);
    CHECK(info->height == 1);
    CHECK(info->frame_count >= 1);

    err = nsgif_frame_prepare(
        gif,
        &area,
        &delay_cs,
        &frame
    );
    CHECK(err == NSGIF_OK);
    err = nsgif_frame_decode(gif, frame, &bitmap);
    CHECK(err == NSGIF_OK && bitmap != NULL);

    nsgif_destroy(gif);

    printf("libnsgif consumer test: %d/8 checks passed\n", checks);
    return EXIT_SUCCESS;
}
