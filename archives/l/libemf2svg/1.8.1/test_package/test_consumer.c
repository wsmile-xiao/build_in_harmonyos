/* Consumer test for libemf2svg: exercise the public API on a hand-crafted
 * minimal EMF (HEADER + EOF records). No data files, no fonts, no network.
 * 9 assertions; exits non-zero on the first failure. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <emf2svg.h>

static void put_u32le(unsigned char *p, uint32_t v) {
    p[0] = (unsigned char)(v & 0xff);
    p[1] = (unsigned char)((v >> 8) & 0xff);
    p[2] = (unsigned char)((v >> 16) & 0xff);
    p[3] = (unsigned char)((v >> 24) & 0xff);
}

static void put_s32le(unsigned char *p, int32_t v) {
    put_u32le(p, (uint32_t)v);
}

/* Build a 108-byte minimal EMF: 88-byte EMR_HEADER + 20-byte EMR_EOF. */
static size_t build_minimal_emf(unsigned char *buf, int32_t right,
                                int32_t bottom) {
    memset(buf, 0, 108);
    put_u32le(buf + 0, 1);          /* iType = EMR_HEADER */
    put_u32le(buf + 4, 88);         /* nSize */
    put_s32le(buf + 8, 0);          /* rclBounds.left */
    put_s32le(buf + 12, 0);         /* rclBounds.top */
    put_s32le(buf + 16, right);     /* rclBounds.right */
    put_s32le(buf + 20, bottom);    /* rclBounds.bottom */
    put_s32le(buf + 24, 0);         /* rclFrame.left */
    put_s32le(buf + 28, 0);         /* rclFrame.top */
    put_s32le(buf + 32, right * 10);  /* rclFrame.right */
    put_s32le(buf + 36, bottom * 10); /* rclFrame.bottom */
    put_u32le(buf + 40, 0x464D4520);  /* dSignature " EMF" */
    put_u32le(buf + 44, 0x00010000);  /* nVersion */
    put_u32le(buf + 48, 108);         /* nBytes */
    put_u32le(buf + 52, 2);           /* nRecords */
    /* nHandles/nDescription/offDescription/nPalEntries stay 0 */
    put_s32le(buf + 72, 1024); /* szlDevice.cx */
    put_s32le(buf + 76, 768);  /* szlDevice.cy */
    put_s32le(buf + 80, 320);  /* szlMillimeters.cx */
    put_s32le(buf + 84, 240);  /* szlMillimeters.cy */
    put_u32le(buf + 88, 14); /* iType = EMR_EOF */
    put_u32le(buf + 92, 20); /* nSize */
    put_u32le(buf + 96, 0);  /* nPalEntries */
    put_u32le(buf + 100, 16); /* offPalEntries */
    put_u32le(buf + 104, 20); /* nSizeLast */
    return 108;
}

static int contains(const char *haystack, size_t len, const char *needle) {
    size_t nlen = strlen(needle);
    size_t i;
    if (nlen == 0 || len < nlen) {
        return 0;
    }
    for (i = 0; i + nlen <= len; i++) {
        if (memcmp(haystack + i, needle, nlen) == 0) {
            return 1;
        }
    }
    return 0;
}

#define CHECK(cond, label)                                                 \
    do {                                                                   \
        if (!(cond)) {                                                     \
            printf("FAIL " label "\n");                                    \
            return 1;                                                      \
        }                                                                  \
        printf("PASS " label "\n");                                        \
    } while (0)

int main(void) {
    unsigned char emf[108];
    generatorOptions options;
    char *svg_out = NULL;
    size_t svg_len = 0;
    int ret;
    bool is_emfp = true;

    /* A1: plain conversion succeeds and yields non-empty SVG. */
    build_minimal_emf(emf, 100, 100);
    memset(&options, 0, sizeof(options));
    options.verbose = false;
    options.emfplus = true;
    options.nameSpace = (char *)"";
    options.svgDelimiter = true;
    options.imgWidth = 0;
    options.imgHeight = 0;
    ret = emf2svg((char *)emf, sizeof(emf), &svg_out, &svg_len, &options);
    CHECK(ret == 1 && svg_out != NULL && svg_len > 0, "convert-minimal-emf");

    /* A2: delimited output carries the XML prolog and svg open/close tags. */
    CHECK(contains(svg_out, svg_len, "<?xml"), "svg-has-xml-prolog");
    CHECK(contains(svg_out, svg_len, "<svg "), "svg-has-open-tag");
    CHECK(contains(svg_out, svg_len, "</svg>"), "svg-has-close-tag");
    free(svg_out);
    svg_out = NULL;

    /* A3: the header-only EMF carries no EMF+ records. */
    ret = emf2svg_is_emfplus((char *)emf, sizeof(emf), &is_emfp);
    CHECK(ret == 1 && is_emfp == false, "is-emfplus-false");

    /* A4: namespace + explicit size options shape the svg root element. */
    memset(&options, 0, sizeof(options));
    options.verbose = false;
    options.emfplus = true;
    options.nameSpace = (char *)"svg";
    options.svgDelimiter = true;
    options.imgWidth = 800;
    options.imgHeight = 600;
    ret = emf2svg((char *)emf, sizeof(emf), &svg_out, &svg_len, &options);
    CHECK(ret == 1 && svg_out != NULL && svg_len > 0, "convert-sized");
    CHECK(contains(svg_out, svg_len, "svg:svg"), "svg-namespace-applied");
    CHECK(contains(svg_out, svg_len, "width="), "svg-width-attr");
    CHECK(contains(svg_out, svg_len, "height="), "svg-height-attr");
    free(svg_out);

    printf("CONSUMER_DONE passed=9/9\n");
    return 0;
}
