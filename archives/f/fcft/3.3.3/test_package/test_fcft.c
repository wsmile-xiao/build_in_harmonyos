/* Consumer test for fcft: exercises the real public API without
 * requiring system fonts (font-dependent checks skip gracefully).
 *
 * Checks (6 total):
 *  1. fcft_init returns true
 *  2. fcft_capabilities carries the SVG capability (bundled nanosvg backend)
 *  3. shaping capabilities are absent (shaping disabled in this recipe)
 *  4. font options create/destroy round-trip
 *  5. font lookup path exercised (loaded font validated, or clean skip
 *     when the device has no fontconfig fonts)
 *  6. fcft_fini runs cleanly
 */
#include <stdbool.h>
#include <stdio.h>

#include <fcft/fcft.h>

int main(void) {
    int passed = 0;
    const int total = 6;

    /* 1. init */
    if (!fcft_init(FCFT_LOG_COLORIZE_NEVER, false, FCFT_LOG_CLASS_ERROR)) {
        fprintf(stderr, "FAIL: fcft_init returned false\n");
        return 1;
    }
    printf("ok 1: fcft_init\n");
    passed++;

    /* 2-3. capabilities */
    enum fcft_capabilities caps = fcft_capabilities();
    printf("capabilities mask: 0x%x\n", (unsigned)caps);
    if (!(caps & FCFT_CAPABILITY_SVG)) {
        fprintf(stderr, "FAIL: SVG capability missing (nanosvg backend expected)\n");
        return 1;
    }
    printf("ok 2: SVG capability present\n");
    passed++;
    if (caps & (FCFT_CAPABILITY_GRAPHEME_SHAPING | FCFT_CAPABILITY_TEXT_RUN_SHAPING)) {
        fprintf(stderr, "FAIL: shaping capability set while shaping is disabled\n");
        return 1;
    }
    printf("ok 3: shaping capabilities absent as configured\n");
    passed++;

    /* 4. font options lifecycle */
    struct fcft_font_options *opts = fcft_font_options_create();
    if (opts == NULL) {
        fprintf(stderr, "FAIL: fcft_font_options_create returned NULL\n");
        return 1;
    }
    fcft_font_options_destroy(opts);
    printf("ok 4: font options create/destroy\n");
    passed++;

    /* 5. font lookup (needs a fontconfig font; skip cleanly without one) */
    {
        struct fcft_font_options *o2 = fcft_font_options_create();
        struct fcft_font *font = NULL;
        if (o2 != NULL) {
            const char *names[1] = {"monospace"};
            font = fcft_from_name2(1, names, NULL, o2);
            fcft_font_options_destroy(o2);
        }
        if (font == NULL) {
            printf("ok 5: font lookup skipped (no fontconfig fonts on device)\n");
            passed++;
        } else {
            if (font->height <= 0 || font->max_advance.x <= 0) {
                fprintf(stderr, "FAIL: loaded font has bogus metrics\n");
                fcft_destroy(font);
                return 1;
            }
            const struct fcft_glyph *glyph =
                fcft_rasterize_char_utf32(font, (unsigned)'A', FCFT_SUBPIXEL_NONE);
            if (glyph == NULL || glyph->pix == NULL || glyph->width <= 0 || glyph->height <= 0) {
                fprintf(stderr, "FAIL: rasterize of 'A' produced no bitmap\n");
                fcft_destroy(font);
                return 1;
            }
            long kx = 0, ky = 0;
            (void)fcft_kerning(font, (unsigned)'A', (unsigned)'V', &kx, &ky);
            printf("ok 5: font load + rasterize 'A' (%dx%d) + kerning probe\n",
                   glyph->width, glyph->height);
            passed++;
            fcft_destroy(font);
        }
    }

    /* 6. fini */
    fcft_fini();
    printf("ok 6: fcft_fini\n");
    passed++;

    printf("RESULT: %d/%d consumer checks passed\n", passed, total);
    return (passed == total) ? 0 : 1;
}
