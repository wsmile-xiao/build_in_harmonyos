#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <id3tag.h>

#define CHECK(cond, msg) do { \
    printf("  [assert] %s: %s\n", (cond) ? "PASS" : "FAIL", msg); \
    if (!(cond)) return 1; \
} while (0)

static int check_string(const char *what, const id3_ucs4_t *ucs4,
                         const char *expected) {
    id3_utf8_t *utf8 = id3_ucs4_utf8duplicate(ucs4);
    CHECK(utf8 != NULL, "id3_ucs4_utf8duplicate returned non-NULL");
    int ok = strcmp((const char *)utf8, expected) == 0;
    printf("  [assert] %s == \"%s\" (expected \"%s\"): %s\n",
           what, (const char *)utf8, expected, ok ? "PASS" : "FAIL");
    free(utf8);
    return ok ? 0 : 1;
}

int main(void) {
    printf("libid3tag version: %s\n", id3_version);

    /* 1. Create a tag */
    struct id3_tag *tag = id3_tag_new();
    CHECK(tag != NULL, "id3_tag_new() returned non-NULL");

    /* 2. Attach a TIT2 (title) text frame and set its value */
    struct id3_frame *frame = id3_frame_new("TIT2");
    CHECK(frame != NULL, "id3_frame_new(\"TIT2\") returned non-NULL");
    id3_tag_attachframe(tag, frame);

    /* field 0: text encoding; field 1: full string */
    union id3_field *enc = id3_frame_field(frame, 0);
    CHECK(enc != NULL, "id3_frame_field(frame, 0) returned non-NULL");
    CHECK(id3_field_settextencoding(enc, ID3_FIELD_TEXTENCODING_UTF_8) == 0,
          "id3_field_settextencoding(UTF_8) succeeded");

    union id3_field *title = id3_frame_field(frame, 1);
    CHECK(title != NULL, "id3_frame_field(frame, 1) returned non-NULL");
    id3_ucs4_t *value = id3_utf8_ucs4duplicate((const id3_utf8_t *)"HarmonyOS Test");
    CHECK(value != NULL, "id3_utf8_ucs4duplicate returned non-NULL");
    /* TIT2 field 1 is a STRINGLIST; addstring duplicates internally,
     * so the caller keeps ownership and must free the original.
     * Evaluate once outside CHECK — the macro's cond must stay pure. */
    int rc = id3_field_addstring(title, value);
    CHECK(rc == 0, "id3_field_addstring succeeded");
    unsigned int nstrings = id3_field_getnstrings(title);
    CHECK(nstrings == 1, "STRINGLIST holds exactly one string");
    free(value);

    /* 3. Render the tag to bytes (ID3v2.4, unsynchronisation off):
     * id3_tag_render(tag, NULL) returns the required length (two-pass mode). */
    id3_length_t length = id3_tag_render(tag, NULL);
    CHECK(length > 0, "id3_tag_render(tag, NULL) returned non-zero length");
    id3_byte_t *rendered = malloc(length);
    CHECK(rendered != NULL, "malloc(render length) returned non-NULL");
    CHECK(id3_tag_render(tag, rendered) == length,
          "second id3_tag_render() pass wrote exactly length bytes");

    /* 4. Parse the rendered bytes back */
    signed long query = id3_tag_query(rendered, length);
    CHECK(query > 0, "id3_tag_query() recognized ID3v2 header");
    struct id3_tag *parsed = id3_tag_parse(rendered, query);
    CHECK(parsed != NULL, "id3_tag_parse() returned non-NULL");

    /* 5. Read the title back */
    struct id3_frame *found = id3_tag_findframe(parsed, "TIT2", 0);
    CHECK(found != NULL, "id3_tag_findframe(parsed, \"TIT2\", 0) found the frame");
    CHECK(id3_field_getnstrings(id3_frame_field(found, 1)) == 1,
          "parsed TIT2 STRINGLIST holds exactly one string");
    if (check_string("title", id3_field_getstrings(id3_frame_field(found, 1), 0),
                     "HarmonyOS Test") != 0)
        return 1;

    /* 6. Version roundtrip check: rendered tag starts with "ID3" magic */
    CHECK(rendered[0] == 'I' && rendered[1] == 'D' && rendered[2] == '3',
          "rendered tag starts with ID3 magic");

    /* Clean up */
    id3_tag_delete(parsed);
    id3_tag_delete(tag);
    free(rendered);

    printf("test libid3tag 0.16.3: OK\n");
    return 0;
}
