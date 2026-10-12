/*
 * test_package/test.c — nanosvg 0.0-git.239e102 consumer assertion suite.
 *
 * Consumer-perspective verification of BOTH shipped libraries:
 *   - parser     (libnanosvg.a):  nsvgParse on an embedded minimal SVG
 *   - rasterizer (libnanosvgrast.a): nsvgCreateRasterizer + nsvgRasterize
 *
 * All assertion anchors were measured on real runs (native + the exact
 * upstream snapshot), e.g. for <svg><path d="M0 0h10v10h-10z"/></svg>:
 *   image 10x10, 1 shape, 1 closed path, npts=13, bounds [0,0,10,10],
 *   default fill = opaque black (0xff000000), 10x10 raster fully covered.
 */
#include <stdio.h>
#include <string.h>
#include <math.h>

#include <nanosvg.h>
#include <nanosvgrast.h>

static int g_pass = 0, g_fail = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (cond) { g_pass++; printf("[ok]   %s\n", msg); }     \
        else      { g_fail++; printf("[FAIL] %s (line %d)\n", msg, __LINE__); } \
    } while (0)

static int feq(float a, float b) { return fabsf(a - b) < 1e-3f; }

/* ── A. Parser: fill shape, no width/height/viewBox attributes ── */
static void test_parse_fill_shape(void)
{
    char svg[] = "<svg><path d=\"M0 0h10v10h-10z\"/></svg>";
    NSVGimage* img = nsvgParse(svg, "px", 96.0f);
    CHECK(img != NULL, "A1 nsvgParse returns non-NULL image");

    int nshapes = 0;
    for (NSVGshape* s = img ? img->shapes : NULL; s; s = s->next) nshapes++;
    CHECK(img && feq(img->width, 10.0f), "A2 image width auto-sized to 10 (shape bounds)");
    CHECK(img && feq(img->height, 10.0f), "A3 image height auto-sized to 10 (shape bounds)");
    CHECK(img && img->shapes != NULL, "A4 shape list non-NULL");
    CHECK(nshapes == 1, "A5 exactly 1 shape parsed");

    NSVGshape* sh = img ? img->shapes : NULL;
    int npaths = 0;
    for (NSVGpath* p = sh ? sh->paths : NULL; p; p = p->next) npaths++;
    CHECK(sh && sh->paths != NULL, "A6 path list non-NULL");
    CHECK(npaths == 1, "A7 exactly 1 path in shape");

    NSVGpath* pa = sh ? sh->paths : NULL;
    CHECK(pa && pa->npts == 13, "A8 path npts == 13 (M + 3 lines closed back to M)");
    CHECK(pa && pa->closed == 1, "A9 path closed flag set");
    CHECK(pa && feq(pa->bounds[0], 0.0f), "A10 path bounds minx == 0");
    CHECK(pa && feq(pa->bounds[1], 0.0f), "A11 path bounds miny == 0");
    CHECK(pa && feq(pa->bounds[2], 10.0f), "A12 path bounds maxx == 10");
    CHECK(pa && feq(pa->bounds[3], 10.0f), "A13 path bounds maxy == 10");
    CHECK(sh && sh->fill.type == NSVG_PAINT_COLOR, "A14 default fill is a solid color paint");
    CHECK(sh && sh->fill.color == 0xff000000u, "A15 default fill color = opaque black (0xff000000)");
    CHECK(sh && sh->stroke.type == NSVG_PAINT_NONE, "A16 default stroke = none");

    if (img) nsvgDelete(img);
}

/* ── B. Rasterizer: scale=1, full coverage of the 10x10 quad ── */
static void test_rasterize_scale1(void)
{
    char svg[] = "<svg><path d=\"M0 0h10v10h-10z\"/></svg>";
    NSVGimage* img = nsvgParse(svg, "px", 96.0f);
    NSVGrasterizer* rast = nsvgCreateRasterizer();
    CHECK(img != NULL && rast != NULL, "B1 rasterizer created");
    if (!img || !rast) {
        if (rast) nsvgDeleteRasterizer(rast);
        if (img) nsvgDelete(img);
        return;
    }

    unsigned char px[10 * 10 * 4];
    memset(px, 0, sizeof(px));
    nsvgRasterize(rast, img, 0, 0, 1.0f, px, 10, 10, 10 * 4);

    int painted = 0;
    for (int i = 0; i < 100; i++)
        if (px[i * 4 + 3] >= 128) painted++;
    CHECK(painted == 100, "B2 scale=1 raster covers all 100 pixels (alpha >= 128)");

    const unsigned char* c = &px[(5 * 10 + 5) * 4];
    CHECK(c[3] == 255, "B3 center pixel alpha == 255");
    CHECK(c[0] == 0 && c[1] == 0 && c[2] == 0, "B4 center pixel RGB = (0,0,0) opaque black");

    if (rast) nsvgDeleteRasterizer(rast);
    if (img) nsvgDelete(img);
}

/* ── C. Rasterizer: scale=2 upscaled, coverage grows accordingly ── */
static void test_rasterize_scale2(void)
{
    char svg[] = "<svg><path d=\"M0 0h10v10h-10z\"/></svg>";
    NSVGimage* img = nsvgParse(svg, "px", 96.0f);
    NSVGrasterizer* rast = nsvgCreateRasterizer();
    CHECK(img != NULL && rast != NULL, "C0 scale-2 inputs created");
    if (!img || !rast) {
        if (rast) nsvgDeleteRasterizer(rast);
        if (img) nsvgDelete(img);
        return;
    }

    unsigned char px[20 * 20 * 4];
    memset(px, 0, sizeof(px));
    nsvgRasterize(rast, img, 0, 0, 2.0f, px, 20, 20, 20 * 4);

    int painted = 0, interior = 0;
    for (int y = 0; y < 20; y++)
        for (int x = 0; x < 20; x++)
            if (px[(y * 20 + x) * 4 + 3] >= 128) {
                painted++;
                if (x > 0 && x < 19 && y > 0 && y < 19) interior++;
            }
    CHECK(painted == 400, "C1 scale=2 raster covers all 400 pixels");
    CHECK(interior == 324, "C2 18x18 interior fully covered (324 pixels)");

    if (rast) nsvgDeleteRasterizer(rast);
    if (img) nsvgDelete(img);
}

/* ── D. Parser: stroke paint + explicit width/height attributes ── */
static void test_parse_stroke_line(void)
{
    char svg[] = "<svg width=\"20\" height=\"20\">"
                 "<line x1=\"0\" y1=\"0\" x2=\"20\" y2=\"20\" "
                 "stroke=\"#ff0000\" stroke-width=\"2\" fill=\"none\"/></svg>";
    NSVGimage* img = nsvgParse(svg, "px", 96.0f);
    CHECK(img != NULL, "D1 stroke SVG parsed non-NULL");

    int nshapes = 0;
    NSVGshape* sh = NULL;
    for (NSVGshape* s = img ? img->shapes : NULL; s; s = s->next) { nshapes++; sh = s; }
    CHECK(img && feq(img->width, 20.0f), "D2 explicit width=20 respected");
    CHECK(img && feq(img->height, 20.0f), "D3 explicit height=20 respected");
    CHECK(nshapes == 1 && sh != NULL, "D4 exactly 1 shape from <line>");
    CHECK(sh && sh->stroke.type == NSVG_PAINT_COLOR, "D5 stroke is a solid color paint");
    CHECK(sh && sh->stroke.color == 0xff0000ffu, "D6 stroke color = opaque red #ff0000 (0xff0000ff)");
    CHECK(sh && sh->fill.type == NSVG_PAINT_NONE, "D7 fill=none respected");
    CHECK(sh && sh->paths && sh->paths->npts == 4, "D8 line converts to path with npts == 4");

    if (img) nsvgDelete(img);
}

int main(void)
{
    printf("nanosvg consumer test — parser + rasterizer\n");
    test_parse_fill_shape();
    test_rasterize_scale1();
    test_rasterize_scale2();
    test_parse_stroke_line();
    printf("\nRESULT: %d passed, %d failed (total %d)\n",
           g_pass, g_fail, g_pass + g_fail);
    return g_fail == 0 ? 0 : 1;
}
