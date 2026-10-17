/* test.c — consumer smoke test for libhoedown 3.0.7.
 *
 * Renders a small Markdown document through the public hoedown API and
 * verifies the produced HTML contains the expected <h1> element, so the
 * test genuinely exercises the packaged library (not an empty shell).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <hoedown/document.h>
#include <hoedown/buffer.h>
#include <hoedown/html.h>

/* bounded substring search: html->data is not guaranteed NUL-terminated */
static int contains(const uint8_t *data, size_t size, const char *needle)
{
    size_t nlen = strlen(needle);
    size_t i;

    if (size < nlen)
        return 0;
    for (i = 0; i + nlen <= size; i++) {
        if (data[i] == (uint8_t)needle[0] &&
            memcmp(data + i, needle, nlen) == 0)
            return 1;
    }
    return 0;
}

int main(void)
{
    const char *md = "# Hello hoedown\n\nThis is **strong** text.\n";
    hoedown_renderer *renderer;
    hoedown_document *doc;
    hoedown_buffer *html;
    int rc = 0;

    renderer = hoedown_html_renderer_new(HOEDOWN_HTML_USE_XHTML, 0);
    if (!renderer) {
        fprintf(stderr, "hoedown_html_renderer_new failed\n");
        return 1;
    }
    doc = hoedown_document_new(renderer, HOEDOWN_EXT_FENCED_CODE, 16);
    if (!doc) {
        fprintf(stderr, "hoedown_document_new failed\n");
        hoedown_html_renderer_free(renderer);
        return 1;
    }
    html = hoedown_buffer_new(64);
    if (!html) {
        fprintf(stderr, "hoedown_buffer_new failed\n");
        hoedown_document_free(doc);
        hoedown_html_renderer_free(renderer);
        return 1;
    }

    hoedown_document_render(doc, html, (const uint8_t *)md, strlen(md));

    if (html->size == 0) {
        fprintf(stderr, "hoedown produced empty output\n");
        rc = 1;
    } else if (!contains(html->data, html->size, "<h1>")) {
        fprintf(stderr, "hoedown output missing <h1>: %.*s\n",
                (int)html->size, (const char *)html->data);
        rc = 1;
    }

    fwrite(html->data, 1, html->size, stdout);
    fputc('\n', stdout);

    hoedown_buffer_free(html);
    hoedown_document_free(doc);
    hoedown_html_renderer_free(renderer);
    return rc;
}
