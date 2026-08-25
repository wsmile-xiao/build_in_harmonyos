/*
 * libnsbmp 0.1.7 Conan test_package
 *
 * Embeds a minimal 2x1 24-bit BMP (red + green pixels), exercises the full
 * upstream create -> analyse -> decode -> finalise API against the freshly
 * built libnsbmp, and asserts width, height, bpp, decode status and the
 * decoded pixel bytes.
 *
 * The embedded BMP and expected pixel values were verified against the
 * upstream test_decode_bmp harness and the library's write_ppm callback
 * convention (4 bytes/pixel, layout [R, G, B, A]).
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#include "libnsbmp.h"

#define BYTES_PER_PIXEL sizeof(uint32_t)

/* ── Bitmap callbacks (same convention as upstream test/decode_bmp.c) ── */
static void *bitmap_create(int width, int height, unsigned int state)
{
    (void)state;
    if (width > 4096 || height > 4096) {
        return NULL;
    }
    return calloc((size_t)width * (size_t)height, BYTES_PER_PIXEL);
}

static unsigned char *bitmap_get_buffer(void *bitmap)
{
    return (unsigned char *)bitmap;
}

static void bitmap_destroy(void *bitmap)
{
    free(bitmap);
}

/* ── Minimal 2x1 24-bit BMP ────────────────────────────────────────────
 * File header (14 bytes) + BITMAPINFOHEADER (40 bytes) + pixel data.
 * Pixel row is padded to a 4-byte boundary: 2 pixels * 3 bytes = 6 bytes,
 * padded to 8 with 2 zero bytes. BMP rows are bottom-up, so the single
 * row holds both pixels: pixel0 = red (00 00 FF), pixel1 = green (00 FF 00).
 */
static const unsigned char minimal_bmp[] = {
    /* BMP file header (14 bytes) */
    0x42, 0x4D,             /* 'BM' signature                          */
    0x3E, 0x00, 0x00, 0x00, /* file size = 62 bytes                    */
    0x00, 0x00,             /* reserved                                */
    0x00, 0x00,             /* reserved                                */
    0x36, 0x00, 0x00, 0x00, /* pixel data offset = 54 bytes            */
    /* BITMAPINFOHEADER (40 bytes) */
    0x28, 0x00, 0x00, 0x00, /* header size = 40                        */
    0x02, 0x00, 0x00, 0x00, /* width  = 2                              */
    0x01, 0x00, 0x00, 0x00, /* height = 1                              */
    0x01, 0x00,             /* planes = 1                              */
    0x18, 0x00,             /* bits per pixel = 24                     */
    0x00, 0x00, 0x00, 0x00, /* compression = BI_RGB (0)                */
    0x08, 0x00, 0x00, 0x00, /* image size = 8 (padded row)             */
    0x00, 0x00, 0x00, 0x00, /* x pixels per metre (unused)             */
    0x00, 0x00, 0x00, 0x00, /* y pixels per metre (unused)             */
    0x00, 0x00, 0x00, 0x00, /* colours = 0 (default 2^bpp)             */
    0x00, 0x00, 0x00, 0x00, /* important colours = 0 (all)             */
    /* Pixel data (8 bytes: 2 pixels * 3 B + 2 B row padding) */
    0x00, 0x00, 0xFF,       /* pixel0 = red   (BGR: 00 00 FF)          */
    0x00, 0xFF, 0x00,       /* pixel1 = green (BGR: 00 FF 00)          */
    0x00, 0x00              /* row padding to 4-byte boundary          */
};

int main(void)
{
    int failures = 0;
    bmp_image bmp;
    bmp_bitmap_callback_vt callbacks = {
        bitmap_create,
        bitmap_destroy,
        bitmap_get_buffer,
    };
    bmp_result result;
    unsigned char *pixels;

    /* --- 1. bmp_create --- */
    result = bmp_create(&bmp, &callbacks);
    if (result != BMP_OK) {
        fprintf(stderr, "FAIL: bmp_create returned %d (expected %d)\n",
                result, BMP_OK);
        failures++;
    } else {
        printf("[OK] bmp_create -> BMP_OK\n");
    }

    /* --- 2. bmp_analyse --- */
    result = bmp_analyse(&bmp, sizeof(minimal_bmp), (uint8_t *)minimal_bmp);
    if (result != BMP_OK) {
        fprintf(stderr, "FAIL: bmp_analyse returned %d (expected %d)\n",
                result, BMP_OK);
        failures++;
    } else {
        printf("[OK] bmp_analyse -> BMP_OK\n");
    }

    /* --- 3. verify dimensions from analyse --- */
    if (bmp.width != 2) {
        fprintf(stderr, "FAIL: width = %u (expected 2)\n", bmp.width);
        failures++;
    } else {
        printf("[OK] width = %u\n", bmp.width);
    }
    if (bmp.height != 1) {
        fprintf(stderr, "FAIL: height = %u (expected 1)\n", bmp.height);
        failures++;
    } else {
        printf("[OK] height = %u\n", bmp.height);
    }
    if (bmp.bpp != 24) {
        fprintf(stderr, "FAIL: bpp = %u (expected 24)\n", bmp.bpp);
        failures++;
    } else {
        printf("[OK] bpp = %u\n", bmp.bpp);
    }

    /* --- 4. bmp_decode --- */
    result = bmp_decode(&bmp);
    if (result != BMP_OK) {
        fprintf(stderr, "FAIL: bmp_decode returned %d (expected %d)\n",
                result, BMP_OK);
        failures++;
    } else {
        printf("[OK] bmp_decode -> BMP_OK\n");
    }
    if (!bmp.decoded) {
        fprintf(stderr, "FAIL: bmp.decoded = false (expected true)\n");
        failures++;
    } else {
        printf("[OK] bmp.decoded = true\n");
    }

    /* --- 5. verify decoded pixel bytes --- */
    pixels = bitmap_get_buffer(bmp.bitmap);
    if (!pixels) {
        fprintf(stderr, "FAIL: decoded pixel buffer is NULL\n");
        failures++;
    } else {
        /* Decoder writes [R, G, B, A] per pixel (4 bytes, uint32_t). */
        unsigned char p0_r = pixels[0], p0_g = pixels[1], p0_b = pixels[2], p0_a = pixels[3];
        unsigned char p1_r = pixels[4], p1_g = pixels[5], p1_b = pixels[6], p1_a = pixels[7];
        printf("[INFO] pixel0 = [0x%02x, 0x%02x, 0x%02x, 0x%02x]\n", p0_r, p0_g, p0_b, p0_a);
        printf("[INFO] pixel1 = [0x%02x, 0x%02x, 0x%02x, 0x%02x]\n", p1_r, p1_g, p1_b, p1_a);

        if (p0_r != 0xFF || p0_g != 0x00 || p0_b != 0x00 || p0_a != 0xFF) {
            fprintf(stderr, "FAIL: pixel0 = [0x%02x,0x%02x,0x%02x,0x%02x]"
                    " (expected red [FF,00,00,FF])\n", p0_r, p0_g, p0_b, p0_a);
            failures++;
        } else {
            printf("[OK] pixel0 = red [FF,00,00,FF]\n");
        }
        if (p1_r != 0x00 || p1_g != 0xFF || p1_b != 0x00 || p1_a != 0xFF) {
            fprintf(stderr, "FAIL: pixel1 = [0x%02x,0x%02x,0x%02x,0x%02x]"
                    " (expected green [00,FF,00,FF])\n", p1_r, p1_g, p1_b, p1_a);
            failures++;
        } else {
            printf("[OK] pixel1 = green [00,FF,00,FF]\n");
        }
    }

    /* --- 6. bmp_finalise (cleanup) --- */
    bmp_finalise(&bmp);
    printf("[OK] bmp_finalise\n");

    /* --- Summary --- */
    if (failures == 0) {
        printf("\n== CHECKS PASSED (8/8) ==\n");
        return 0;
    }
    fprintf(stderr, "\n== CHECKS FAILED (%d) ==\n", failures);
    return 1;
}
