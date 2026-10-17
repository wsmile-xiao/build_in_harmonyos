#include <stdio.h>
#include <string.h>

#include <raqm.h>

/* Consumer test for raqm 0.11.0 on HarmonyOS PC.
 *
 * Exercises the raqm public API lifecycle without an external font file
 * (font-driven layout coverage is provided by the 51 upstream meson tests
 * which run inside conan create using the fonts shipped in the release
 * tarball; this consumer test must not carry a large binary asset through
 * the PR diff). Asserts: version string, raqm_t lifecycle, UTF-8 text
 * setting with mixed Arabic/Latin content, RTL paragraph direction, the
 * documented no-font behaviour of the glyph query, and linkability against
 * libraqm + its freetype/harfbuzz/fribidi dependency chain.
 */
int main(void) {
    if (strcmp(raqm_version_string(), "0.11.0") != 0) {
        fprintf(stderr, "unexpected raqm version: %s\n", raqm_version_string());
        return 1;
    }

    raqm_t *rq = raqm_create();
    if (rq == NULL) {
        fprintf(stderr, "raqm_create failed\n");
        return 1;
    }

    /* Mixed-direction payload: Arabic run wrapped around a Latin run
     * (same payload as upstream test-1.test). */
    const char *text =
        "\xd8\xb9\xd8\xb1\xd8\xa8\xd9\x8a (English) \xd8\xb9\xd8\xb1\xd8\xa8\xd9\x8a";
    if (!raqm_set_text_utf8(rq, text, strlen(text))) {
        fprintf(stderr, "raqm_set_text_utf8 failed\n");
        raqm_destroy(rq);
        return 1;
    }

    if (!raqm_set_par_direction(rq, RAQM_DIRECTION_RTL)) {
        fprintf(stderr, "raqm_set_par_direction failed\n");
        raqm_destroy(rq);
        return 1;
    }

    /* Without an attached font, raqm_layout() must report failure (every
     * character needs a face) and the glyph query must return an empty
     * result — verified against the 0.11.0 implementation. */
    if (raqm_layout(rq)) {
        fprintf(stderr, "raqm_layout unexpectedly succeeded without a font\n");
        raqm_destroy(rq);
        return 1;
    }

    size_t count = 12345;
    raqm_glyph_t *glyphs = raqm_get_glyphs(rq, &count);
    if (glyphs != NULL || count != 0) {
        fprintf(stderr, "unexpected glyph result without a font: %p %zu\n",
                (void *)glyphs, count);
        raqm_destroy(rq);
        return 1;
    }

    raqm_destroy(rq);
    printf("raqm 0.11.0 API lifecycle: PASS (no-font path, empty glyphs)\n");
    return 0;
}
