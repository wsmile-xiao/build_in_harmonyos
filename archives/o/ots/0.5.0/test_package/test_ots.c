/* Installed-package consumer test for ots 0.5.0.
 *
 * Exercises the installed libots-1 through its public
 * <libots-1/ots/libots.h> API with a real summarization pipeline:
 * parse a multi-sentence English article, grade it, highlight 50%,
 * then verify the text and HTML summaries are non-empty and shorter
 * than the input (i.e. summarization really happened, not a stub).
 *
 * Check 1: ots_parse_stream yields lines and words.
 * Check 2: ots_grade_doc assigns a document title.
 * Check 3: highlight + ots_get_doc_text/ots_get_doc_HTML produce
 *          non-empty summaries shorter than the source text.
 */
#include <stdio.h>
#include <string.h>

#include <libots-1/ots/libots.h>

static const char sample_text[] =
    "OpenHarmony is an open source operating system for smart devices.\n"
    "OpenHarmony supports phones tablets watches and embedded boards.\n"
    "The OpenHarmony kernel abstracts drivers for many device vendors.\n"
    "Developers build OpenHarmony applications with the ArkTS language.\n"
    "ArkTS applications run on the Ark runtime with fast startup.\n"
    "The OpenHarmony community contributes drivers docs and test suites.\n"
    "OpenHarmony documentation covers kernel subsystems and the SDK.\n"
    "Vendors ship OpenHarmony phones watches and industrial terminals.\n";

int main(void)
{
    OtsArticle *art = ots_new_article();
    size_t in_len, text_len = 0, html_len = 0;
    unsigned char *text_out = NULL;
    unsigned char *html_out = NULL;
    int word_count;
    int rc = 0;

    if (art == NULL) {
        fprintf(stderr, "FAIL: ots_new_article returned NULL\n");
        return 1;
    }

    /* Dictionary first: ots_parse_stream only breaks lines on the
     * ParserBreak postfixes (".", "?", "!" ...) loaded from en.xml
     * (parser.c ots_parser_should_break + dictionary.c linebreak rules).
     * Without ots_load_xml_dictionary the break list is empty and
     * lineCount stays 1 no matter how many newlines the input has. */
    if (!ots_load_xml_dictionary(art, (const unsigned char *)"en")) {
        fprintf(stderr, "FAIL: ots_load_xml_dictionary(en) failed\n");
        rc = 1;
        goto done;
    }

    /* Check 1: parse produces lines and words. */
    in_len = strlen(sample_text);
    ots_parse_stream((const unsigned char *)sample_text, in_len, art);
    word_count = ots_get_article_word_count(art);
    if (art->lineCount < 3 || word_count <= 0) {
        fprintf(stderr, "FAIL: parse yielded lineCount=%d words=%d\n",
                art->lineCount, word_count);
        rc = 2;
        goto done;
    }
    printf("PASS: parse produced %d lines, %d words\n", art->lineCount, word_count);

    /* Check 2: grading assigns a document title. */
    ots_grade_doc(art);
    if (art->title == NULL || art->title[0] == '\0') {
        fprintf(stderr, "FAIL: ots_grade_doc left title empty\n");
        rc = 3;
        goto done;
    }
    printf("PASS: grade assigned title \"%s\"\n", art->title);

    /* Check 3: summaries are non-empty and shorter than the input. */
    ots_highlight_doc(art, 50);
    text_out = ots_get_doc_text(art, &text_len);
    html_out = ots_get_doc_HTML(art, &html_len);
    if (text_out == NULL || text_len == 0) {
        fprintf(stderr, "FAIL: text summary is empty\n");
        rc = 4;
        goto done;
    }
    if (html_out == NULL || html_len == 0) {
        fprintf(stderr, "FAIL: HTML summary is empty\n");
        rc = 5;
        goto done;
    }
    if (text_len >= in_len) {
        fprintf(stderr, "FAIL: summary not shorter than input (%u >= %u)\n",
                (unsigned)text_len, (unsigned)in_len);
        rc = 6;
        goto done;
    }
    if (text_out[0] == '\0' || html_out[0] == '\0') {
        fprintf(stderr, "FAIL: summary buffers start with NUL\n");
        rc = 7;
        goto done;
    }
    printf("PASS: summaries non-empty and shorter (text %u < %u, html %u bytes)\n",
           (unsigned)text_len, (unsigned)in_len, (unsigned)html_len);

    printf("OK: ots 0.5.0 summarize pipeline passed\n");
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
           "\"command\":\"./test_ots\",\"discovered\":3,\"passedCount\":3}\n");

done:
    if (text_out != NULL)
        g_free(text_out);
    if (html_out != NULL)
        g_free(html_out);
    ots_free_article(art);
    return rc;
}
