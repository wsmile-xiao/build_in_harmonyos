#include <hb.h>
#include <hb-ot.h>
#include <hb-icu.h>

#include <stdio.h>

int main(void) {
    const char text[] = "Harmony";
    hb_buffer_t *buffer = hb_buffer_create();
    if (buffer == NULL || !hb_buffer_allocation_successful(buffer)) {
        fprintf(stderr, "HarfBuzz buffer allocation failed\n");
        if (buffer != NULL) {
            hb_buffer_destroy(buffer);
        }
        return 1;
    }
    if (!hb_version_atleast(14, 4, 0)) {
        fprintf(stderr, "Unexpected HarfBuzz version: %s\n", hb_version_string());
        hb_buffer_destroy(buffer);
        return 1;
    }

    hb_buffer_add_utf8(buffer, text, -1, 0, -1);
    hb_buffer_guess_segment_properties(buffer);
    hb_shape(hb_font_get_empty(), buffer, NULL, 0);

    unsigned int glyph_count = hb_buffer_get_length(buffer);
    unsigned int info_count = 0;
    unsigned int position_count = 0;
    hb_glyph_info_t *infos = hb_buffer_get_glyph_infos(buffer, &info_count);
    hb_glyph_position_t *positions = hb_buffer_get_glyph_positions(
        buffer, &position_count
    );
    if (glyph_count != 7 || infos == NULL || positions == NULL ||
        info_count != glyph_count || position_count != glyph_count) {
        fprintf(stderr, "Unexpected shaping result\n");
        hb_buffer_destroy(buffer);
        return 1;
    }

    /* New in 14.3.0. Empty faces return zero, but the symbol must link and run. */
    if (hb_ot_fetch_number(
            hb_face_get_empty(), HB_OT_NUMBER_TAG_FONT_X_MIN) != 0) {
        fprintf(stderr, "Unexpected empty-face OpenType number\n");
        hb_buffer_destroy(buffer);
        return 1;
    }

    /* ICU component (libharfbuzz-icu): hb_icu_script_to_script must link and
     * round-trip a known script (used by WebKitGTK ComplexTextController). */
    if (hb_icu_script_to_script(USCRIPT_LATIN) != HB_SCRIPT_LATIN) {
        fprintf(stderr, "Unexpected ICU script mapping\n");
        hb_buffer_destroy(buffer);
        return 1;
    }

    hb_buffer_destroy(buffer);
    printf("harfbuzz 14.4.0.1 shaping, fetch, and ICU APIs: PASS (%u glyphs)\n", glyph_count);
    return 0;
}
