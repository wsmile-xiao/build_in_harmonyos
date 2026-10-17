/* libsvg consumer test: parse real SVG content through the public API and
 * assert on what the render engine callbacks actually receive.
 *
 * libsvg calls every engine callback unconditionally (no NULL checks in
 * _svg_style_render), so the recording engine must implement the complete
 * svg_render_engine_t interface.
 *
 * Covers: svg_create/destroy, svg_parse_buffer, svg_parse_chunk_{begin,chunk,end},
 * svg_render with a callback engine (viewport, view_box, rect, path geometry,
 * fill/stroke colors), svg_get_size, and negative tests (malformed SVG must
 * return SVG_STATUS_PARSE_ERROR; missing file must return
 * SVG_STATUS_FILE_NOT_FOUND).
 */
#include <stdio.h>
#include <string.h>
#include <math.h>

#include "svg.h"

static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (cond) { \
        printf("ok - %s\n", msg); \
    } else { \
        failures++; \
        printf("FAIL - %s\n", msg); \
    } \
} while (0)

#define CHECK_NEAR(a, b, msg) CHECK(fabs((a) - (b)) < 1e-6, msg)

/* --- recording render engine --- */

typedef struct {
    /* viewport / view box */
    int      viewport_calls;
    double   viewport_w, viewport_h;
    int      view_box_calls;
    double   vb_x, vb_y, vb_w, vb_h;

    /* rect */
    int      rect_calls;
    double   rect_x, rect_y, rect_w, rect_h, rect_rx, rect_ry;

    /* path geometry */
    int      move_to_calls, line_to_calls, curve_to_calls, close_path_calls;
    double   last_mx, last_my, last_lx, last_ly;
    double   last_c1x, last_c1y, last_c2x, last_c2y, last_c3x, last_c3y;

    /* style */
    int      fill_paint_calls;
    int      last_fill_rgb;
    int      stroke_paint_calls;
    int      last_stroke_rgb;
    double   last_stroke_width;

    int      render_path_calls;
    int      begin_group_calls, end_group_calls;
} recorder_t;

static svg_status_t rec_begin_group (void *c, double opacity) {
    recorder_t *r = c; r->begin_group_calls++; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_begin_element (void *c) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_end_element (void *c) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_end_group (void *c, double opacity) {
    recorder_t *r = c; r->end_group_calls++; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_move_to (void *c, double x, double y) {
    recorder_t *r = c; r->move_to_calls++; r->last_mx = x; r->last_my = y; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_line_to (void *c, double x, double y) {
    recorder_t *r = c; r->line_to_calls++; r->last_lx = x; r->last_ly = y; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_curve_to (void *c, double x1, double y1,
                                  double x2, double y2,
                                  double x3, double y3) {
    recorder_t *r = c;
    r->curve_to_calls++;
    r->last_c1x = x1; r->last_c1y = y1;
    r->last_c2x = x2; r->last_c2y = y2;
    r->last_c3x = x3; r->last_c3y = y3;
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_quadratic_curve_to (void *c, double x1, double y1,
                                            double x2, double y2) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_arc_to (void *c, double rx, double ry,
                                double x_axis_rotation, int large_arc_flag,
                                int sweep_flag, double x, double y) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_close_path (void *c) {
    recorder_t *r = c; r->close_path_calls++; return SVG_STATUS_SUCCESS;
}
/* style callbacks: full set — libsvg calls them unconditionally */
static svg_status_t rec_set_color (void *c, const svg_color_t *color) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_fill_opacity (void *c, double fill_opacity) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_fill_paint (void *c, const svg_paint_t *paint) {
    recorder_t *r = c;
    if (paint->type == SVG_PAINT_TYPE_COLOR) {
        r->fill_paint_calls++;
        r->last_fill_rgb = paint->p.color.rgb;
    }
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_fill_rule (void *c, svg_fill_rule_t fill_rule) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_font_family (void *c, const char *family) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_font_size (void *c, double size) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_font_style (void *c, svg_font_style_t font_style) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_font_weight (void *c, unsigned int font_weight) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_opacity (void *c, double opacity) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_dash_array (void *c, double *dash_array, int num_dashes) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_dash_offset (void *c, svg_length_t *offset) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_line_cap (void *c, svg_stroke_line_cap_t line_cap) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_line_join (void *c, svg_stroke_line_join_t line_join) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_miter_limit (void *c, double limit) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_opacity (void *c, double stroke_opacity) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_paint (void *c, const svg_paint_t *paint) {
    recorder_t *r = c;
    if (paint->type == SVG_PAINT_TYPE_COLOR) {
        r->stroke_paint_calls++;
        r->last_stroke_rgb = paint->p.color.rgb;
    }
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_stroke_width (void *c, svg_length_t *width) {
    recorder_t *r = c; r->last_stroke_width = width->value; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_text_anchor (void *c, svg_text_anchor_t text_anchor) {
    return SVG_STATUS_SUCCESS;
}
/* transform */
static svg_status_t rec_transform (void *closure, double a, double b, double c1,
                                   double d, double e, double f) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_apply_view_box (void *c, svg_view_box_t view_box,
                                        svg_length_t *width, svg_length_t *height) {
    recorder_t *r = c;
    r->view_box_calls++;
    r->vb_x = view_box.box.x; r->vb_y = view_box.box.y;
    r->vb_w = view_box.box.width; r->vb_h = view_box.box.height;
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_set_viewport_dimension (void *c, svg_length_t *width,
                                                svg_length_t *height) {
    recorder_t *r = c;
    r->viewport_calls++;
    r->viewport_w = width->value; r->viewport_h = height->value;
    return SVG_STATUS_SUCCESS;
}
/* drawing */
static svg_status_t rec_render_line (void *c, svg_length_t *x1, svg_length_t *y1,
                                     svg_length_t *x2, svg_length_t *y2) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_render_path (void *c) {
    recorder_t *r = c; r->render_path_calls++; return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_render_ellipse (void *c, svg_length_t *cx, svg_length_t *cy,
                                        svg_length_t *rx, svg_length_t *ry) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_render_rect (void *c, svg_length_t *x, svg_length_t *y,
                                     svg_length_t *width, svg_length_t *height,
                                     svg_length_t *rx, svg_length_t *ry) {
    recorder_t *r = c;
    r->rect_calls++;
    r->rect_x = x->value; r->rect_y = y->value;
    r->rect_w = width->value; r->rect_h = height->value;
    r->rect_rx = rx->value; r->rect_ry = ry->value;
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_render_text (void *c, svg_length_t *x, svg_length_t *y,
                                     const char *utf8) {
    return SVG_STATUS_SUCCESS;
}
static svg_status_t rec_render_image (void *c, unsigned char *data,
                                      unsigned int data_width, unsigned int data_height,
                                      svg_length_t *x, svg_length_t *y,
                                      svg_length_t *width, svg_length_t *height) {
    return SVG_STATUS_SUCCESS;
}

static svg_render_engine_t make_engine (void) {
    svg_render_engine_t e;
    memset (&e, 0, sizeof (e));
    e.begin_group            = rec_begin_group;
    e.begin_element          = rec_begin_element;
    e.end_element            = rec_end_element;
    e.end_group              = rec_end_group;
    e.move_to                = rec_move_to;
    e.line_to                = rec_line_to;
    e.curve_to               = rec_curve_to;
    e.quadratic_curve_to     = rec_quadratic_curve_to;
    e.arc_to                 = rec_arc_to;
    e.close_path             = rec_close_path;
    e.set_color              = rec_set_color;
    e.set_fill_opacity       = rec_set_fill_opacity;
    e.set_fill_paint         = rec_set_fill_paint;
    e.set_fill_rule          = rec_set_fill_rule;
    e.set_font_family        = rec_set_font_family;
    e.set_font_size          = rec_set_font_size;
    e.set_font_style         = rec_set_font_style;
    e.set_font_weight        = rec_set_font_weight;
    e.set_opacity            = rec_set_opacity;
    e.set_stroke_dash_array  = rec_set_stroke_dash_array;
    e.set_stroke_dash_offset = rec_set_stroke_dash_offset;
    e.set_stroke_line_cap    = rec_set_stroke_line_cap;
    e.set_stroke_line_join   = rec_set_stroke_line_join;
    e.set_stroke_miter_limit = rec_set_stroke_miter_limit;
    e.set_stroke_opacity     = rec_set_stroke_opacity;
    e.set_stroke_paint       = rec_set_stroke_paint;
    e.set_stroke_width       = rec_set_stroke_width;
    e.set_text_anchor        = rec_set_text_anchor;
    e.transform              = rec_transform;
    e.apply_view_box         = rec_apply_view_box;
    e.set_viewport_dimension = rec_set_viewport_dimension;
    e.render_line            = rec_render_line;
    e.render_path            = rec_render_path;
    e.render_ellipse         = rec_render_ellipse;
    e.render_rect            = rec_render_rect;
    e.render_text            = rec_render_text;
    e.render_image           = rec_render_image;
    return e;
}

/* --- test 1: minimal <svg> with viewBox + width/height --- */

static void test_minimal_svg (void) {
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"200\" height=\"100\""
        " viewBox=\"10 20 200 100\"></svg>";

    svg_t *svg = NULL;
    svg_status_t status;
    svg_render_engine_t engine = make_engine ();
    recorder_t rec;
    svg_length_t w, h;

    memset (&rec, 0, sizeof (rec));

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status == SVG_STATUS_SUCCESS, "minimal svg parses without error");

    svg_get_size (svg, &w, &h);
    CHECK_NEAR(w.value, 200.0, "svg_get_size reports width=200");
    CHECK_NEAR(h.value, 100.0, "svg_get_size reports height=100");

    status = svg_render (svg, &engine, &rec);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_render succeeds");
    CHECK(rec.viewport_calls == 1, "viewport dimension delivered once");
    CHECK_NEAR(rec.viewport_w, 200.0, "viewport width=200");
    CHECK_NEAR(rec.viewport_h, 100.0, "viewport height=100");
    CHECK(rec.view_box_calls == 1, "viewBox delivered once");
    CHECK_NEAR(rec.vb_x, 10.0, "viewBox x=10");
    CHECK_NEAR(rec.vb_y, 20.0, "viewBox y=20");
    CHECK_NEAR(rec.vb_w, 200.0, "viewBox width=200");
    CHECK_NEAR(rec.vb_h, 100.0, "viewBox height=100");

    svg_destroy (svg);
}

/* --- test 2: <rect> with fill color and rounded corners --- */

static void test_rect (void) {
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\">"
        "<rect x=\"5\" y=\"6\" width=\"40\" height=\"30\" rx=\"2\" ry=\"3\""
        " fill=\"#010203\"/>"
        "</svg>";

    svg_t *svg = NULL;
    svg_status_t status;
    svg_render_engine_t engine = make_engine ();
    recorder_t rec;

    memset (&rec, 0, sizeof (rec));

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (rect test)");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status == SVG_STATUS_SUCCESS, "rect svg parses without error");

    status = svg_render (svg, &engine, &rec);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_render succeeds (rect test)");
    CHECK(rec.rect_calls == 1, "one rect rendered");
    CHECK_NEAR(rec.rect_x, 5.0, "rect x=5");
    CHECK_NEAR(rec.rect_y, 6.0, "rect y=6");
    CHECK_NEAR(rec.rect_w, 40.0, "rect width=40");
    CHECK_NEAR(rec.rect_h, 30.0, "rect height=30");
    CHECK_NEAR(rec.rect_rx, 2.0, "rect rx=2");
    CHECK_NEAR(rec.rect_ry, 3.0, "rect ry=3");
    CHECK(rec.fill_paint_calls >= 1, "fill paint delivered");
    CHECK(rec.last_fill_rgb == 0x010203, "fill color parsed as #010203");

    svg_destroy (svg);
}

/* --- test 3: <path> geometry via move/line/curve/close --- */

static void test_path (void) {
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"100\" height=\"100\">"
        "<path d=\"M 10 20 L 30 40 C 50 60 70 80 90 100 Z\""
        " fill=\"none\" stroke=\"#ff0000\" stroke-width=\"2.5\"/>"
        "</svg>";

    svg_t *svg = NULL;
    svg_status_t status;
    svg_render_engine_t engine = make_engine ();
    recorder_t rec;

    memset (&rec, 0, sizeof (rec));

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (path test)");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status == SVG_STATUS_SUCCESS, "path svg parses without error");

    status = svg_render (svg, &engine, &rec);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_render succeeds (path test)");
    CHECK(rec.move_to_calls == 1, "path produced one move_to");
    CHECK_NEAR(rec.last_mx, 10.0, "move_to x=10");
    CHECK_NEAR(rec.last_my, 20.0, "move_to y=20");
    CHECK(rec.line_to_calls == 1, "path produced one line_to");
    CHECK_NEAR(rec.last_lx, 30.0, "line_to x=30");
    CHECK_NEAR(rec.last_ly, 40.0, "line_to y=40");
    CHECK(rec.curve_to_calls == 1, "path produced one curve_to");
    CHECK_NEAR(rec.last_c1x, 50.0, "curve_to p1 x=50");
    CHECK_NEAR(rec.last_c1y, 60.0, "curve_to p1 y=60");
    CHECK_NEAR(rec.last_c2x, 70.0, "curve_to p2 x=70");
    CHECK_NEAR(rec.last_c2y, 80.0, "curve_to p2 y=80");
    CHECK_NEAR(rec.last_c3x, 90.0, "curve_to p3 x=90");
    CHECK_NEAR(rec.last_c3y, 100.0, "curve_to p3 y=100");
    CHECK(rec.close_path_calls == 1, "path closed");
    CHECK(rec.render_path_calls == 1, "path rendered once");
    CHECK(rec.stroke_paint_calls >= 1, "stroke paint delivered");
    CHECK(rec.last_stroke_rgb == 0xff0000, "stroke color parsed as #ff0000");
    CHECK_NEAR(rec.last_stroke_width, 2.5, "stroke-width=2.5");

    svg_destroy (svg);
}

/* --- test 4: chunked parsing produces identical results --- */

static void test_chunked_parse (void) {
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"80\" height=\"60\">"
        "<rect x=\"1\" y=\"2\" width=\"10\" height=\"20\" fill=\"#0a0b0c\"/>"
        "</svg>";

    svg_t *svg = NULL;
    svg_status_t status;
    svg_render_engine_t engine = make_engine ();
    recorder_t rec;

    memset (&rec, 0, sizeof (rec));

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (chunk test)");

    status = svg_parse_chunk_begin (svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_parse_chunk_begin succeeds");

    /* feed the document in three uneven chunks */
    status  = svg_parse_chunk (svg, doc, 40);
    CHECK(status == SVG_STATUS_SUCCESS, "chunk 1 accepted");
    status  = svg_parse_chunk (svg, doc + 40, 13);
    CHECK(status == SVG_STATUS_SUCCESS, "chunk 2 accepted");
    status  = svg_parse_chunk (svg, doc + 53, strlen (doc) - 53);
    CHECK(status == SVG_STATUS_SUCCESS, "chunk 3 accepted");

    status = svg_parse_chunk_end (svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_parse_chunk_end succeeds");

    status = svg_render (svg, &engine, &rec);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_render succeeds (chunk test)");
    CHECK(rec.rect_calls == 1, "chunked parse produced one rect");
    CHECK_NEAR(rec.rect_w, 10.0, "chunked rect width=10");
    CHECK_NEAR(rec.rect_h, 20.0, "chunked rect height=20");
    CHECK(rec.last_fill_rgb == 0x0a0b0c, "chunked fill color #0a0b0c");

    svg_destroy (svg);
}

/* --- test 5 (negative): malformed SVG must report a parse error --- */

static void test_negative_malformed (void) {
    /* fatal XML syntax error inside the document: libxml2 flags the
     * push-parser context as not well-formed, which libsvg converts to
     * SVG_STATUS_PARSE_ERROR at _svg_parser_end() time. */
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\">"
        "<<badmarkup></svg>";

    svg_t *svg = NULL;
    svg_status_t status;

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (negative test)");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status == SVG_STATUS_PARSE_ERROR,
          "malformed SVG returns SVG_STATUS_PARSE_ERROR");

    svg_destroy (svg);
}

/* --- test 5b (negative): tag mismatch must report a parse error --- */

static void test_negative_tag_mismatch (void) {
    /* closing tag does not match the opening tag: libxml2 flags the
     * push-parser context as not well-formed at terminate time. */
    static const char *doc =
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"10\" height=\"10\">"
        "<rect x=\"5\" y=\"6\" width=\"7\" height=\"8\"/></xsvg>";

    svg_t *svg = NULL;
    svg_status_t status;
    svg_render_engine_t engine = make_engine ();
    recorder_t rec;

    memset (&rec, 0, sizeof (rec));

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (tag mismatch test)");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status == SVG_STATUS_PARSE_ERROR,
          "tag mismatch returns SVG_STATUS_PARSE_ERROR");

    /* Note: the <rect/> element is fully parsed and delivered before the
     * mismatched end tag aborts the document, so libsvg does render it.
     * The observable contract is the PARSE_ERROR status asserted above. */
    status = svg_render (svg, &engine, &rec);
    CHECK(status == SVG_STATUS_SUCCESS, "render after parse error is survivable");

    svg_destroy (svg);
}

/* --- test 6 (negative): garbage must not parse as success --- */

static void test_negative_garbage (void) {
    static const char *doc = "this is << not >> svg at all";
    svg_t *svg = NULL;
    svg_status_t status;

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (garbage test)");

    status = svg_parse_buffer (svg, doc, strlen (doc));
    CHECK(status != SVG_STATUS_SUCCESS,
          "garbage input does not report success");

    svg_destroy (svg);
}

/* --- test 7 (negative): missing file must report FILE_NOT_FOUND --- */

static void test_negative_missing_file (void) {
    svg_t *svg = NULL;
    svg_status_t status;

    status = svg_create (&svg);
    CHECK(status == SVG_STATUS_SUCCESS, "svg_create succeeds (missing file test)");

    status = svg_parse (svg, "/nonexistent/path/does-not-exist.svg");
    CHECK(status == SVG_STATUS_FILE_NOT_FOUND,
          "missing file returns SVG_STATUS_FILE_NOT_FOUND");

    svg_destroy (svg);
}

int main (void) {
    test_minimal_svg ();
    test_rect ();
    test_path ();
    test_chunked_parse ();
    test_negative_malformed ();
    test_negative_tag_mismatch ();
    test_negative_garbage ();
    test_negative_missing_file ();

    printf ("\nlibsvg test summary: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
