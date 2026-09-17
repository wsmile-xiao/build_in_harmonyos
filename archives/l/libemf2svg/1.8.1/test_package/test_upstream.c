/* Upstream-path test for libemf2svg: drive the same emf2svg() entry point
 * that tests/resources/check_correctness.sh exercises through emf2svg-conv
 * (the conv tool itself needs glibc argp, absent on OHOS, so the library
 * entry point is driven directly). 3 cases; exits non-zero on failure. */
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

static size_t build_emf(unsigned char *buf, size_t cap, int32_t right,
                        int32_t bottom, int with_eof) {
    size_t total = with_eof ? 108 : 88;
    if (cap < total) {
        return 0;
    }
    memset(buf, 0, total);
    put_u32le(buf + 0, 1);
    put_u32le(buf + 4, 88);
    put_s32le(buf + 8, 0);
    put_s32le(buf + 12, 0);
    put_s32le(buf + 16, right);
    put_s32le(buf + 20, bottom);
    put_s32le(buf + 24, 0);
    put_s32le(buf + 28, 0);
    put_s32le(buf + 32, right * 10);
    put_s32le(buf + 36, bottom * 10);
    put_u32le(buf + 40, 0x464D4520);
    put_u32le(buf + 44, 0x00010000);
    put_u32le(buf + 48, (uint32_t)total);
    put_u32le(buf + 52, with_eof ? 2 : 1);
    put_s32le(buf + 72, 1024);
    put_s32le(buf + 76, 768);
    put_s32le(buf + 80, 320);
    put_s32le(buf + 84, 240);
    if (with_eof) {
        put_u32le(buf + 88, 14);
        put_u32le(buf + 92, 20);
        put_u32le(buf + 96, 0);
        put_u32le(buf + 100, 16);
        put_u32le(buf + 104, 20);
    }
    return total;
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

static void default_options(generatorOptions *options) {
    memset(options, 0, sizeof(*options));
    options->verbose = false;
    options->emfplus = true;
    options->nameSpace = (char *)"";
    options->svgDelimiter = true;
    options->imgWidth = 0;
    options->imgHeight = 0;
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
    unsigned char emf_a[108];
    unsigned char emf_b[108];
    unsigned char emf_trunc[88];
    generatorOptions options;
    char *out_a = NULL;
    char *out_b = NULL;
    char *out_t = NULL;
    size_t len_a = 0;
    size_t len_b = 0;
    size_t len_t = 0;
    size_t la;
    size_t lb;
    size_t lt;
    int ret;

    /* U1: well-formed EMF converts to non-empty tagged SVG. */
    la = build_emf(emf_a, sizeof(emf_a), 100, 100, 1);
    default_options(&options);
    ret = emf2svg((char *)emf_a, la, &out_a, &len_a, &options);
    CHECK(ret == 1 && out_a != NULL && len_a > 0, "upstream-convert-ok");
    CHECK(contains(out_a, len_a, "<svg "), "upstream-svg-open");
    CHECK(contains(out_a, len_a, "</svg>"), "upstream-svg-close");

    /* U2: different bounds convert to different SVG (content-dependent,
     * guards against canned-output false passes). */
    lb = build_emf(emf_b, sizeof(emf_b), 200, 50, 1);
    default_options(&options);
    ret = emf2svg((char *)emf_b, lb, &out_b, &len_b, &options);
    CHECK(ret == 1 && out_b != NULL && len_b > 0, "upstream-variant-ok");
    CHECK(len_b != len_a || memcmp(out_a, out_b,
                                   len_a < len_b ? len_a : len_b) != 0,
          "upstream-output-varies");

    /* U3: truncated EMF (header only, no EOF) is rejected, mirroring the
     * corrupt-input handling of check_correctness.sh. */
    lt = build_emf(emf_trunc, sizeof(emf_trunc), 100, 100, 0);
    default_options(&options);
    ret = emf2svg((char *)emf_trunc, lt, &out_t, &len_t, &options);
    CHECK(ret == 0, "upstream-truncated-rejected");
    free(out_t);

    free(out_a);
    free(out_b);
    printf("UPSTREAM_DONE passed=3/3\n");
    return 0;
}
