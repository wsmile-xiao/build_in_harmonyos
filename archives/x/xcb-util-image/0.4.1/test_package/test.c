/* xcb-util-image 0.4.1 consumer link + API smoke test.
 *
 * Exercises xcb_image_create and xcb_image_create_from_bitmap_data
 * which create image structures without needing an X server connection.
 * Verifies basic image properties and calls xcb_image_destroy.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <xcb/xcb.h>
#include <xcb/xcb_image.h>

int main(void) {
    /* 1. Create a basic 8x8 Z-pixmap image (no connection needed) */
    xcb_image_t *img = xcb_image_create(
        8,                          /* width */
        8,                          /* height */
        XCB_IMAGE_FORMAT_Z_PIXMAP,  /* format */
        32,                         /* xpad */
        32,                         /* depth */
        32,                         /* bpp */
        32,                         /* unit */
        XCB_IMAGE_ORDER_LSB_FIRST,  /* byte_order */
        XCB_IMAGE_ORDER_LSB_FIRST,  /* bit_order */
        NULL,                       /* base */
        0,                          /* bytes */
        NULL                        /* data */
    );
    if (img == NULL) {
        fprintf(stderr, "xcb_image_create returned NULL\n");
        return 1;
    }

    /* 2. Verify image properties */
    if (img->width != 8) {
        fprintf(stderr, "image width != 8 (got %d)\n", img->width);
        xcb_image_destroy(img);
        return 2;
    }
    if (img->height != 8) {
        fprintf(stderr, "image height != 8 (got %d)\n", img->height);
        xcb_image_destroy(img);
        return 3;
    }
    if (img->format != XCB_IMAGE_FORMAT_Z_PIXMAP) {
        fprintf(stderr, "image format != Z_PIXMAP\n");
        xcb_image_destroy(img);
        return 4;
    }

    /* 3. Destroy the image (must be safe) */
    xcb_image_destroy(img);

    /* 4. Create an image from bitmap data (no connection needed) */
    uint8_t bitmap_data[] = {
        0x01, 0x00, 0x00, 0x00,
        0x03, 0x00, 0x00, 0x00,
        0x07, 0x00, 0x00, 0x00,
        0x0f, 0x00, 0x00, 0x00,
    };
    xcb_image_t *bitmap = xcb_image_create_from_bitmap_data(
        bitmap_data,    /* data */
        8,              /* width */
        4               /* height */
    );
    if (bitmap == NULL) {
        fprintf(stderr, "xcb_image_create_from_bitmap_data returned NULL\n");
        return 5;
    }

    /* 5. Verify bitmap image properties */
    if (bitmap->width != 8) {
        fprintf(stderr, "bitmap width != 8 (got %d)\n", bitmap->width);
        xcb_image_destroy(bitmap);
        return 6;
    }

    /* 6. Destroy the bitmap image */
    xcb_image_destroy(bitmap);

    if (printf("xcb-util-image api smoke ok\n") < 0) {
        return 7;
    }
    return 0;
}
