#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define QOI_IMPLEMENTATION
#include "qoi.h"

static int g_failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (cond) { \
            printf("  [PASS] %s\n", msg); \
        } else { \
            printf("  [FAIL] %s\n", msg); \
            g_failures++; \
        } \
    } while (0)

int main(void)
{
    unsigned char pixels[4 * 4 * 3];
    unsigned char *encoded = NULL;
    unsigned char *decoded = NULL;
    qoi_desc desc;
    qoi_desc out_desc;
    int encoded_len = 0;
    int i;

    printf("qoi 0-git20251213 OHOS test\n");

    for (i = 0; i < 16; i++) {
        pixels[i * 3 + 0] = (unsigned char)((i * 17) & 0xff);
        pixels[i * 3 + 1] = (unsigned char)((255 - i * 11) & 0xff);
        pixels[i * 3 + 2] = 64;
    }

    memset(&desc, 0, sizeof(desc));
    desc.width = 4;
    desc.height = 4;
    desc.channels = 3;
    desc.colorspace = QOI_SRGB;

    encoded = (unsigned char *)qoi_encode(pixels, &desc, &encoded_len);
    CHECK(encoded != NULL, "qoi_encode returns buffer");
    CHECK(encoded_len > 14, "qoi_encode length includes header");

    memset(&out_desc, 0, sizeof(out_desc));
    decoded = (unsigned char *)qoi_decode(encoded, encoded_len, &out_desc, 3);
    CHECK(decoded != NULL, "qoi_decode returns buffer");
    CHECK(out_desc.width == 4, "decoded width is 4");
    CHECK(out_desc.height == 4, "decoded height is 4");
    CHECK(out_desc.channels == 3, "decoded channels is 3");
    CHECK(out_desc.colorspace == QOI_SRGB, "decoded colorspace is sRGB");
    CHECK(decoded && memcmp(decoded, pixels, sizeof(pixels)) == 0,
          "decoded pixels match source");

    free(encoded);
    free(decoded);

    if (g_failures == 0) {
        printf("HMBS_TEST_PACKAGE_RESULT: PASS\n");
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d)\n", g_failures);
    return 1;
}
