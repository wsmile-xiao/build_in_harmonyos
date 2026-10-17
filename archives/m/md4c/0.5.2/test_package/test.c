/*
 * test.c — Consumer test for the md4c Conan package (0.5.2).
 *
 * Links against the md4c library produced by `conan create` (not the source
 * tree or a host-installed copy) and exercises the real SAX-like parser API:
 * md_parse() drives the MD_PARSER callbacks. We verify that:
 *   1. md_parse() returns 0 (success) on a simple document.
 *   2. The enter_block callback fires for MD_BLOCK_DOC and MD_BLOCK_H.
 *   3. The MD_BLOCK_H detail carries the expected heading level (1).
 *   4. The text callback delivers the heading text "Title".
 *   5. The enter_span callback fires for MD_SPAN_STRONG on **bold** text.
 *   6. The text callback delivers the bold inner text "bold".
 *
 * If any callback is not invoked as expected, the test exits non-zero.
 */
#include <stdio.h>
#include <string.h>
#include "md4c.h"

/* Accumulated state from callbacks, checked at the end. */
struct check_state {
    int saw_doc;
    int saw_heading;
    unsigned heading_level;
    int saw_strong;
    int saw_heading_text_title;
    int saw_bold_text_bold;
};

static int cb_enter_block(MD_BLOCKTYPE type, void *detail, void *userdata)
{
    struct check_state *st = (struct check_state *)userdata;
    switch (type) {
    case MD_BLOCK_DOC:
        st->saw_doc = 1;
        break;
    case MD_BLOCK_H: {
        MD_BLOCK_H_DETAIL *hd = (MD_BLOCK_H_DETAIL *)detail;
        st->saw_heading = 1;
        st->heading_level = hd->level;
        break;
    }
    default:
        break;
    }
    return 0;
}

static int cb_leave_block(MD_BLOCKTYPE type, void *detail, void *userdata)
{
    (void)type;
    (void)detail;
    (void)userdata;
    return 0;
}

static int cb_enter_span(MD_SPANTYPE type, void *detail, void *userdata)
{
    struct check_state *st = (struct check_state *)userdata;
    (void)detail;
    if (type == MD_SPAN_STRONG) {
        st->saw_strong = 1;
    }
    return 0;
}

static int cb_leave_span(MD_SPANTYPE type, void *detail, void *userdata)
{
    (void)type;
    (void)detail;
    (void)userdata;
    return 0;
}

static int cb_text(MD_TEXTTYPE type, const MD_CHAR *text, MD_SIZE size, void *userdata)
{
    struct check_state *st = (struct check_state *)userdata;
    /* Heading text "Title" and bold inner text "bold" are normal text. */
    if (type == MD_TEXT_NORMAL) {
        if (size == 5 && strncmp(text, "Title", 5) == 0) {
            st->saw_heading_text_title = 1;
        }
        if (size == 4 && strncmp(text, "bold", 4) == 0) {
            st->saw_bold_text_bold = 1;
        }
    }
    return 0;
}

static void cb_debug_log(const char *msg, void *userdata)
{
    (void)userdata;
    fprintf(stderr, "[md4c debug] %s\n", msg);
}

int main(void)
{
    /* A minimal Markdown document: an ATX heading and bold inline text. */
    static const char input[] = "# Title\n\nThis is **bold** text.\n";

    struct MD_PARSER parser;
    struct check_state st;
    int rc;

    memset(&st, 0, sizeof(st));
    memset(&parser, 0, sizeof(parser));
    parser.abi_version = 0;
    parser.flags = MD_DIALECT_COMMONMARK;
    parser.enter_block = cb_enter_block;
    parser.leave_block = cb_leave_block;
    parser.enter_span = cb_enter_span;
    parser.leave_span = cb_leave_span;
    parser.text = cb_text;
    parser.debug_log = cb_debug_log;
    parser.syntax = NULL;

    rc = md_parse(input, (MD_SIZE)strlen(input), &parser, &st);
    if (rc != 0) {
        printf("FAIL: md_parse returned %d (expected 0)\n", rc);
        return 1;
    }

    int failures = 0;
    if (!st.saw_doc) {
        printf("FAIL: enter_block(MD_BLOCK_DOC) was not called\n");
        failures++;
    }
    if (!st.saw_heading) {
        printf("FAIL: enter_block(MD_BLOCK_H) was not called\n");
        failures++;
    }
    if (st.saw_heading && st.heading_level != 1) {
        printf("FAIL: heading level = %u (expected 1)\n", st.heading_level);
        failures++;
    }
    if (!st.saw_heading_text_title) {
        printf("FAIL: text callback did not deliver heading text \"Title\"\n");
        failures++;
    }
    if (!st.saw_strong) {
        printf("FAIL: enter_span(MD_SPAN_STRONG) was not called for **bold**\n");
        failures++;
    }
    if (!st.saw_bold_text_bold) {
        printf("FAIL: text callback did not deliver bold inner text \"bold\"\n");
        failures++;
    }

    if (failures > 0) {
        printf("FAIL: %d callback assertion(s) failed\n", failures);
        return 1;
    }

    printf("All md4c parser callback tests passed!\n");
    return 0;
}
