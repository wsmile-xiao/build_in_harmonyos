/* Consumer test for sail 0.9.10 on HarmonyOS PC.
 *
 * Real API usage:
 *   1. sail_codec_bundle_list()      — enumerate enabled codecs, must be non-empty
 *   2. sail_codec_info_from_name()   — look up the PNG codec by name
 *   3. sail_load_from_memory()       — actually decode a hardcoded 2x2 24-bit BMP,
 *                                      then verify dimensions via sail_image fields
 *
 * The HMBS_TEST_PACKAGE_RESULT JSON marker is emitted on stdout only after the
 * real assertions complete; numbers come from the true case count.
 */
#include <sail/sail.h>

#include <cstdio>
#include <cstring>
#include <cstdlib>

static void put_u16(unsigned char *dst, unsigned v) {
    dst[0] = (unsigned char)(v & 0xFF);
    dst[1] = (unsigned char)((v >> 8) & 0xFF);
}

static void put_u32(unsigned char *dst, unsigned v) {
    dst[0] = (unsigned char)(v & 0xFF);
    dst[1] = (unsigned char)((v >> 8) & 0xFF);
    dst[2] = (unsigned char)((v >> 16) & 0xFF);
    dst[3] = (unsigned char)((v >> 24) & 0xFF);
}

/* Build a minimal 2x2 24-bit BMP (BI_RGB, bottom-up) into buf; returns size. */
static size_t build_bmp(unsigned char *buf) {
    size_t off = 0;
    /* BITMAPFILEHEADER */
    buf[off++] = 'B'; buf[off++] = 'M';
    put_u32(buf + off, 70); off += 4;          /* file size */
    put_u16(buf + off, 0);  off += 2;          /* reserved */
    put_u16(buf + off, 0);  off += 2;          /* reserved */
    put_u32(buf + off, 54); off += 4;          /* pixel data offset */
    /* BITMAPINFOHEADER */
    put_u32(buf + off, 40); off += 4;          /* header size */
    put_u32(buf + off, 2);  off += 4;          /* width */
    put_u32(buf + off, 2);  off += 4;          /* height (bottom-up) */
    put_u16(buf + off, 1);  off += 2;          /* planes */
    put_u16(buf + off, 24); off += 2;          /* bpp */
    put_u32(buf + off, 0);  off += 4;          /* BI_RGB */
    put_u32(buf + off, 0);  off += 4;          /* image size */
    put_u32(buf + off, 0);  off += 4;          /* x ppm */
    put_u32(buf + off, 0);  off += 4;          /* y ppm */
    put_u32(buf + off, 0);  off += 4;          /* colors used */
    put_u32(buf + off, 0);  off += 4;          /* important colors */
    /* Pixel data: row size = ceil(2*3/4)*4 = 8 bytes; bottom row first. */
    const unsigned char rows[2][8] = {
        { 255, 0,   0,   0,   0, 255, 0,   0 }, /* bottom: px0 blue, px1 green */
        { 0,   0,   255, 0,   255, 0,   0,   0 }, /* top:    px2 red,  px3 blue */
    };
    memcpy(buf + off, rows[0], 8); off += 8;
    memcpy(buf + off, rows[1], 8); off += 8;
    return off;
}

int main(void) {
    const int discovered = 3;
    int passed = 0;

    /* Case 1: the codec bundle must be non-empty (at least one codec enabled). */
    const sail_codec_bundle_node *node = sail_codec_bundle_list();
    if (node == NULL) {
        std::printf("FAIL: sail_codec_bundle_list() returned NULL\n");
    } else {
        int count = 0;
        for (const sail_codec_bundle_node *p = node; p != NULL; p = p->next) {
            ++count;
        }
        std::printf("enabled codec count = %d\n", count);
        if (count > 0) {
            ++passed;
        } else {
            std::printf("FAIL: no codecs enabled\n");
        }
    }

    /* Case 2: PNG codec must be discoverable by name. */
    const sail_codec_info *info = NULL;
    if (sail_codec_info_from_name("png", &info) != SAIL_OK || info == NULL) {
        std::printf("FAIL: sail_codec_info_from_name(\"png\") failed\n");
    } else {
        std::printf("found codec: %s\n", info->name);
        if (info->load_features != NULL && info->name != NULL && info->name[0] != '\0') {
            ++passed;
        } else {
            std::printf("FAIL: png codec info incomplete\n");
        }
    }

    /* Case 3: actually decode a hardcoded 2x2 BMP from memory. */
    unsigned char bmp[512];
    size_t bmp_size = build_bmp(bmp);
    struct sail_image *image = NULL;
    sail_status_t st = sail_load_from_memory(bmp, bmp_size, &image);
    if (st != SAIL_OK || image == NULL) {
        std::printf("FAIL: sail_load_from_memory(bmp) status=%d\n", (int)st);
    } else {
        std::printf("decoded %ux%u, bytes_per_line=%u\n",
                    image->width, image->height, image->bytes_per_line);
        if (image->width == 2 && image->height == 2 && image->pixels != NULL) {
            ++passed;
        } else {
            std::printf("FAIL: unexpected decoded dimensions\n");
        }
        sail_destroy_image(image);
    }

    std::printf("sail consumer: %d/%d cases passed\n", passed, discovered);

    const bool ok = (passed == discovered);
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
                "\"command\":\"test_sail\",\"discovered\":%d,\"passedCount\":%d}\n",
                ok ? "true" : "false", discovered, passed);
    return ok ? 0 : 1;
}
