/* Consumer test for pdfgen 0.1.0 — exercises the packaged static library
 * the way a downstream project does: creates a document, exercises the
 * full API surface (pages, text, shapes, bookmarks, error handling) and
 * saves a PDF whose structure is then asserted by run_check.sh.
 * This is a condensed port of the upstream tests/main.c coverage (data
 * files are synthesized in-code instead of shipped in data/). */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "pdfgen.h"

static int failures = 0;
#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
    else { printf("ok: %s\n", msg); } \
} while (0)

/* 16x8 RGB24 gradient strip (upstream uses tests/rgb.c's data) */
static unsigned char rgb_data[16 * 8 * 3];

int main(void)
{
    struct pdf_info info = {.creator = "My software",
                            .producer = "My software",
                            .title = "My document",
                            .author = "My name",
                            .subject = "My subject"};
    struct pdf_doc *pdf = pdf_create(PDF_A4_WIDTH, PDF_A4_HEIGHT, &info);
    float width, height;
    int err, bm;

    CHECK(pdf != NULL, "pdf_create");
    if (!pdf)
        return 1;

    CHECK(pdf_width(pdf) == PDF_A4_WIDTH &&
          pdf_height(pdf) == PDF_A4_HEIGHT, "A4 page size");

    CHECK(pdf_get_font_text_width(pdf, "Times-BoldItalic", "foo", 14,
                                  &width) == 0 && width > 18,
          "font text width");

    /* pre-page calls must fail */
    CHECK(pdf_add_text(pdf, NULL, "Page One", 10, 20, 30,
                       PDF_RGB(0xff, 0, 0)) < 0, "add_text before page fails");
    CHECK(pdf_add_bookmark(pdf, NULL, -1, "Another Page") < 0,
          "bookmark before page fails");
    CHECK(pdf_get_err(pdf, &err) != NULL, "pending error surfaced");
    pdf_clear_err(pdf);

    /* page 1: text, wrapping, shapes */
    pdf_set_font(pdf, "Times-BoldItalic");
    pdf_append_page(pdf);
    pdf_add_text_wrap(pdf, NULL,
                      "This is a great big long string that I hope will wrap "
                      "properly around several lines.\nThere are some odd "
                      "length linesthatincludelongwords to check the "
                      "justification. I've put some embedded line breaks in "
                      "to see how it copes with them. Hopefully it all works "
                      "properly.\n\n\nWe even include multiple breaks",
                      16, 60, 800, PDF_RGB(0, 0, 0), 300, PDF_ALIGN_JUSTIFY,
                      &height);
    pdf_add_rectangle(pdf, NULL, 58, 816, 304, -height, 2, PDF_RGB(0, 0, 0));
    pdf_add_line(pdf, NULL, 10, 24, 100, 24, 4, PDF_RGB(0xff, 0, 0));
    pdf_add_cubic_bezier(pdf, NULL, 10, 100, 150, 100, 20, 30, 60, 30, 4,
                         PDF_RGB(0, 0xff, 0));
    pdf_add_quadratic_bezier(pdf, NULL, 10, 140, 150, 140, 50, 160, 4,
                             PDF_RGB(0, 0, 0xff));
    pdf_add_circle(pdf, NULL, 100, 240, 50, 5, PDF_RGB(0xff, 0, 0),
                   PDF_TRANSPARENT);
    pdf_add_ellipse(pdf, NULL, 100, 240, 40, 30, 2, PDF_RGB(0xff, 0xff, 0),
                    PDF_RGB(0, 0, 0));
    pdf_add_rectangle(pdf, NULL, 150, 150, 100, 100, 4, PDF_RGB(0, 0, 0xff));
    pdf_add_filled_rectangle(pdf, NULL, 150, 450, 100, 100, 4,
                             PDF_RGB(0, 0xff, 0));
    {
        float p1X[] = {200, 200, 300, 300};
        float p1Y[] = {200, 300, 200, 300};
        pdf_add_polygon(pdf, NULL, p1X, p1Y, 4, 4, PDF_RGB(0xaa, 0xff, 0xee));
        float p2X[] = {400, 400, 500, 500};
        float p2Y[] = {400, 500, 400, 500};
        pdf_add_filled_polygon(pdf, NULL, p2X, p2Y, 4, 4,
                               PDF_RGB(0xff, 0x77, 0x77));
    }
    pdf_add_barcode(pdf, NULL, PDF_BARCODE_128A, 50, 300, 200, 50, "Code128",
                    PDF_RGB(0, 0, 0));
    pdf_add_barcode(pdf, NULL, PDF_BARCODE_39, 50, 400, 400, 50, "CODE39",
                    PDF_RGB(0, 0, 0));
    bm = pdf_add_bookmark(pdf, NULL, -1, "First page");
    CHECK(bm >= 0, "bookmark added");

    /* page 2: utf8 + control characters */
    pdf_append_page(pdf);
    pdf_add_text(pdf, NULL, "Page Two", 10, 20, 30, PDF_RGB(0, 0, 0));
    pdf_add_text(pdf, NULL, "Special characters: €ÜŽžŠšÁáüöäÄÜÖß",
                 10, 50, 15, PDF_RGB(0, 0, 0));
    pdf_add_text(pdf, NULL,
                 "Control characters ( ) < > [ ] { } / % ending",
                 10, 50, 45, PDF_RGB(0, 0, 0));

    /* page 3: rgb24 raw image (synthesized gradient, 16x8) */
    pdf_append_page(pdf);
    for (int y = 0; y < 8; y++)
        for (int x = 0; x < 16; x++) {
            rgb_data[(y * 16 + x) * 3 + 0] = (unsigned char)(x * 16);
            rgb_data[(y * 16 + x) * 3 + 1] = (unsigned char)(y * 32);
            rgb_data[(y * 16 + x) * 3 + 2] = 0x80;
        }
    pdf_add_rgb24(pdf, NULL, 72, 72, 288, 144, rgb_data, 16, 8);
    pdf_page_set_size(pdf, NULL, PDF_A3_HEIGHT, PDF_A3_WIDTH);

    /* page 4: A3 landscape */
    pdf_append_page(pdf);
    pdf_page_set_size(pdf, NULL, PDF_A3_HEIGHT, PDF_A3_WIDTH);
    pdf_add_text(pdf, NULL, "This is an A3 landscape page", 10, 20, 30,
                 PDF_RGB(0xff, 0, 0));

    pdf_save(pdf, "output.pdf");

    const char *err_str = pdf_get_err(pdf, &err);
    CHECK(err_str == NULL, "no pdf errors");
    if (err_str)
        fprintf(stderr, "PDF Error: %d - %s\n", err, err_str);
    pdf_destroy(pdf);

    printf("failures=%d\n", failures);
    return failures ? 1 : 0;
}
