/* Consumer test for libsvg-cairo 0.1.6 on HarmonyOS PC (aarch64).
 *
 * Parses an SVG document from an in-source string (no binary fixture),
 * renders it onto a pure headless cairo image surface (no X11), and
 * asserts the rendered pixels change deterministically. Also checks
 * that a malformed SVG is rejected with a non-success status.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <cairo.h>
#include <svg-cairo.h>

/* Deterministic SVG fixture authored in-source for auditability.
 * A 40x40 white background with an opaque black 10..30 square:
 * pixels inside the square must flip from white (255) to black (0). */
static const char *SVG_FIXTURE =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
    "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"40\" height=\"40\">\n"
    "  <rect x=\"0\" y=\"0\" width=\"40\" height=\"40\" fill=\"white\"/>\n"
    "  <rect x=\"10\" y=\"10\" width=\"20\" height=\"20\" fill=\"black\"/>\n"
    "</svg>\n";

/* Malformed document: mismatched end tag (</span> closes nothing) and a
 * duplicate attribute — both are well-formedness errors libxml2 reports
 * while parsing the chunk, so the push parser flags them without an
 * explicit terminate call. (libsvg's parser never terminates the chunk
 * stream, so a merely truncated document would NOT be detected.) */
static const char *SVG_BROKEN =
    "<?xml version=\"1.0\"?>\n"
    "<svg xmlns=\"http://www.w3.org/2000/svg\" x=\"1\" x=\"2\">"
    "<rect x=\"0\" y=\"0\" width=\"1\" height=\"1\"/></span></svg>\n";

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                            \
    do {                                                            \
        checks++;                                                   \
        if (cond) {                                                 \
            printf("ok %2d - %s\n", checks, msg);                   \
        } else {                                                    \
            printf("not ok %2d - %s\n", checks, msg);               \
            failures++;                                             \
        }                                                           \
    } while (0)

int main(void)
{
    svg_cairo_t *svgc = NULL;
    cairo_surface_t *surface = NULL;
    cairo_t *cr = NULL;
    unsigned char *pixels = NULL;
    unsigned int width = 0, height = 0;
    svg_cairo_status_t status;
    int stride, i, changed_before, changed_after;

    /* 1. svg_cairo_create */
    status = svg_cairo_create(&svgc);
    CHECK(status == SVG_CAIRO_STATUS_SUCCESS, "svg_cairo_create returns success");
    CHECK(svgc != NULL, "svg_cairo_create sets a non-NULL handle");

    /* 2. svg_cairo_parse_buffer with the in-source fixture */
    status = svg_cairo_parse_buffer(svgc, SVG_FIXTURE, strlen(SVG_FIXTURE));
    CHECK(status == SVG_CAIRO_STATUS_SUCCESS, "svg_cairo_parse_buffer accepts valid SVG");

    /* 3. svg_cairo_get_size reflects the document dimensions */
    svg_cairo_get_size(svgc, &width, &height);
    CHECK(width == 40, "svg_cairo_get_size reports width 40");
    CHECK(height == 40, "svg_cairo_get_size reports height 40");

    /* 4. cairo_image_surface_create (pure headless, no display server) */
    stride = cairo_format_stride_for_width(CAIRO_FORMAT_ARGB32, (int)width);
    CHECK(stride > 0, "cairo_format_stride_for_width returns a positive stride");
    /* stride is cairo's bytes-per-row and pixels is byte-typed, so this
     * allocates exactly stride * height bytes: never less than cairo's
     * stride * height requirement, and no extra 4x factor. */
    pixels = (unsigned char *)calloc((size_t)stride * (size_t)height, sizeof(*pixels));
    CHECK(pixels != NULL, "pixel buffer allocation succeeds");
    surface = cairo_image_surface_create_for_data(pixels, CAIRO_FORMAT_ARGB32,
                                                  (int)width, (int)height, stride);
    CHECK(cairo_surface_status(surface) == CAIRO_STATUS_SUCCESS,
          "cairo_image_surface_create_for_data succeeds");
    cr = cairo_create(surface);
    CHECK(cairo_status(cr) == CAIRO_STATUS_SUCCESS, "cairo_create succeeds");

    /* White background before render: the fixture rect fills 40x40 white
     * first, but the surface starts zeroed; count non-zero pixels now. */
    changed_before = 0;
    for (i = 0; i < (int)stride * (int)height; i++)
        if (pixels[i])
            changed_before++;

    /* 5. svg_cairo_render */
    status = svg_cairo_render(svgc, cr);
    CHECK(status == SVG_CAIRO_STATUS_SUCCESS, "svg_cairo_render returns success");

    /* 6. cairo_image_surface_get_data + deterministic pixel change:
     * center pixel (20,20) is inside the black square: its byte channels
     * must be 0; corner pixel (2,2) is on the white rect: channels 255. */
    {
        unsigned char *data = cairo_image_surface_get_data(surface);
        unsigned char *center, *corner;
        CHECK(data != NULL, "cairo_image_surface_get_data returns non-NULL");
        cairo_surface_flush(surface);
        center = data + 20 * stride + 20 * 4;
        corner = data + 2 * stride + 2 * 4;
        CHECK(center[0] == 0 && center[1] == 0 && center[2] == 0,
              "center pixel (inside black rect) renders to black");
        CHECK(corner[0] == 255 && corner[1] == 255 && corner[2] == 255,
              "corner pixel (on white rect) renders to white");
    }

    /* Whole-surface change count after render must exceed the pre-render
     * count (deterministic, not a fixed golden image). */
    changed_after = 0;
    for (i = 0; i < (int)stride * (int)height; i++)
        if (pixels[i])
            changed_after++;
    CHECK(changed_after > changed_before,
          "rendered surface has strictly more non-zero bytes than before");

    /* 7. Malformed SVG must return a non-success status. */
    status = svg_cairo_parse_buffer(svgc, SVG_BROKEN, strlen(SVG_BROKEN));
    CHECK(status != SVG_CAIRO_STATUS_SUCCESS, "malformed SVG is rejected");

    /* 8. svg_cairo_destroy */
    /* Compile-time API contract check: the strongly-typed pointer below
     * must fail to compile if svg_cairo_destroy's return type (or
     * parameter type) ever changes. */
    svg_cairo_status_t (*destroy_with_status)(svg_cairo_t *) =
        svg_cairo_destroy;
    status = destroy_with_status(svgc);
    svgc = NULL;
    CHECK(status == SVG_CAIRO_STATUS_SUCCESS, "svg_cairo_destroy returns success");

    cairo_destroy(cr);
    cairo_surface_destroy(surface);
    free(pixels);

    printf("1..%d\n", checks);
    return failures ? 1 : 0;
}
