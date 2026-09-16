/*
 * Consumer test for the libcaca package — real API calls against the
 * installed library, headless (no display driver is created).
 *
 * Exits non-zero as soon as any check fails, so ctest's exit code is the
 * verdict.  Checks cover the surfaces a consumer actually depends on:
 * version metadata, canvas geometry, character/attribute round-trip,
 * dirty-rectangle bookkeeping, the caca-native export/import codec and the
 * bitmap dithering path.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <caca.h>

static int checks = 0;
static int failures = 0;

static void check(int condition, const char *what)
{
    checks++;
    if (condition) {
        printf("ok %d - %s\n", checks, what);
    } else {
        failures++;
        printf("not ok %d - %s\n", checks, what);
    }
}

int main(void)
{
    char const *version = caca_get_version();
    check(version != NULL && strstr(version, "0.99.beta20") != NULL,
          "caca_get_version() reports 0.99.beta20");

    caca_canvas_t *cv = caca_create_canvas(40, 20);
    check(cv != NULL, "caca_create_canvas(40, 20) returns a canvas");
    if (cv == NULL) {
        printf("1..%d\n", checks);
        return failures ? EXIT_FAILURE : EXIT_SUCCESS;
    }
    check(caca_get_canvas_width(cv) == 40, "canvas width is 40");
    check(caca_get_canvas_height(cv) == 20, "canvas height is 20");

    caca_set_color_ansi(cv, CACA_WHITE, CACA_BLUE);
    caca_put_str(cv, 1, 1, "libcaca");
    check(caca_get_char(cv, 1, 1) == 'l', "caca_put_str places 'l' at (1,1)");
    check(caca_get_char(cv, 7, 1) == 'a', "caca_put_str places 'a' at (7,1)");
    check(caca_attr_to_ansi_fg(caca_get_attr(cv, 1, 1)) == CACA_WHITE,
          "foreground attribute round-trips as white");

    check(caca_get_dirty_rect_count(cv) > 0,
          "drawing marks at least one dirty rectangle");

    size_t exported = 0;
    void *blob = caca_export_canvas_to_memory(cv, "caca", &exported);
    check(blob != NULL && exported > 0,
          "caca_export_canvas_to_memory(\"caca\") produces a payload");

    char const * const *formats = caca_get_export_list();
    check(formats != NULL && formats[0] != NULL,
          "caca_get_export_list() lists at least one codec");

    if (blob != NULL) {
        caca_canvas_t *reimported = caca_create_canvas(0, 0);
        check(reimported != NULL, "second canvas created for re-import");
        if (reimported != NULL) {
            ssize_t imported = caca_import_canvas_from_memory(
                reimported, blob, exported, "caca");
            check(imported >= 0, "caca_import_canvas_from_memory succeeds");
            check(caca_get_canvas_width(reimported) == 40,
                  "re-imported canvas keeps width 40");
            check(caca_get_canvas_height(reimported) == 20,
                  "re-imported canvas keeps height 20");
            check(caca_get_char(reimported, 1, 1) == 'l',
                  "re-imported canvas keeps the text content");
            caca_free_canvas(reimported);
        }
        free(blob);
    }

    /* 4x4 RGBA bitmap, all opaque red; dithered to ASCII it must produce
     * printable output covering the requested area. */
    unsigned char pixels[4 * 4 * 4];
    for (size_t i = 0; i < sizeof(pixels); i += 4) {
        pixels[i + 0] = 0xff;
        pixels[i + 1] = 0x00;
        pixels[i + 2] = 0x00;
        pixels[i + 3] = 0xff;
    }
    caca_dither_t *dither = caca_create_dither(32, 4, 4, 4 * 4,
                                               0x000000ff, 0x0000ff00,
                                               0x00ff0000, 0xff000000);
    check(dither != NULL, "caca_create_dither(32bpp RGBA) succeeds");
    if (dither != NULL) {
        caca_set_dither_charset(dither, "ascii");
        caca_canvas_t *target = caca_create_canvas(16, 8);
        int rc = caca_dither_bitmap(target, 0, 0, 16, 8, dither, pixels);
        check(rc == 0, "caca_dither_bitmap returns 0");
        int rendered = 0;
        for (int y = 0; y < 8; y++) {
            for (int x = 0; x < 16; x++) {
                if (caca_get_char(target, x, y) != ' ') {
                    rendered++;
                }
            }
        }
        check(rendered > 0, "dithered bitmap writes characters into the canvas");
        caca_free_canvas(target);
        caca_free_dither(dither);
    }

    caca_free_canvas(cv);

    printf("1..%d\n", checks);
    printf("# %d checks, %d failures\n", checks, failures);
    return failures ? EXIT_FAILURE : EXIT_SUCCESS;
}
