// test_package/test.cpp — R34: substantive libagg 2.5 API tests
//
// Exercises the real rendering pipeline headlessly: rasterizer + scanline
// renderer into an in-memory pixel buffer, verifying geometry coverage and
// colors at programmatic paths (no golden files):
//   1. solid rectangle fill (exact color, alpha=255)
//   2. anti-aliased stroked line (conv_stroke) at full-coverage rows
//   3. anti-aliased triangle: interior solid via nonzero fill rule
//   4. blending: 50% alpha red over black → R≈127, opaque alpha
//   5. degenerate/boundary inputs (zero-area polygon, off-canvas polygon,
//      1x1 minimal buffer)
//
// Pixel layout note: agg::pixfmt_bgra32 stores bytes in BGRA order
// (B at offset 0, R at offset 2); rgba8(r,g,b,a) is the logical color.
#include <agg2/agg_basics.h>
#include <agg2/agg_rendering_buffer.h>
#include <agg2/agg_pixfmt_rgba.h>
#include <agg2/agg_renderer_base.h>
#include <agg2/agg_renderer_scanline.h>
#include <agg2/agg_rasterizer_scanline_aa.h>
#include <agg2/agg_scanline_p.h>
#include <agg2/agg_path_storage.h>
#include <agg2/agg_conv_stroke.h>

#include <cstdio>
#include <cstring>
#include <cstdlib>

static int g_failures = 0;
static int g_checks = 0;

static void check(bool ok, const char* what) {
    ++g_checks;
    if (!ok) {
        ++g_failures;
        printf("FAIL: %s\n", what);
    }
}

// BGRA channel indices in the raw buffer
enum { CH_B = 0, CH_G = 1, CH_R = 2, CH_A = 3 };

static unsigned pix(unsigned char* buf, int w, int x, int y, int ch) {
    return buf[(size_t)y * w * 4 + (size_t)x * 4 + ch];
}

int main(void) {
    const int W = 64, H = 64;
    unsigned char* buf = new unsigned char[W * H * 4];

    // ── 1. solid rectangle: exact color, no antialiasing artifacts ──
    memset(buf, 0, W * H * 4);
    {
        agg::rendering_buffer rb(buf, W, H, W * 4);
        agg::pixfmt_bgra32 pixf(rb);
        agg::renderer_base<agg::pixfmt_bgra32> renb(pixf);
        agg::rasterizer_scanline_aa<> ras;
        agg::scanline_p8 sl;
        renb.clear(agg::rgba8(0, 0, 0, 255));
        ras.reset();
        ras.move_to_d(10.0, 10.0);
        ras.line_to_d(50.0, 10.0);
        ras.line_to_d(50.0, 30.0);
        ras.line_to_d(10.0, 30.0);
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(255, 0, 0, 255));
        // interior: pure red (R channel at offset 2)
        check(pix(buf, W, 30, 20, CH_R) == 255, "rect interior R==255");
        check(pix(buf, W, 30, 20, CH_G) == 0,   "rect interior G==0");
        check(pix(buf, W, 30, 20, CH_B) == 0,   "rect interior B==0");
        check(pix(buf, W, 30, 20, CH_A) == 255, "rect interior A==255");
        // outside: black background preserved
        check(pix(buf, W, 5, 5, CH_R) == 0 && pix(buf, W, 5, 5, CH_A) == 255,
              "outside remains opaque black");
    }

    // ── 2. anti-aliased stroked line: full coverage at center rows ──
    memset(buf, 0, W * H * 4);
    {
        agg::rendering_buffer rb(buf, W, H, W * 4);
        agg::pixfmt_bgra32 pixf(rb);
        agg::renderer_base<agg::pixfmt_bgra32> renb(pixf);
        agg::rasterizer_scanline_aa<> ras;
        agg::scanline_p8 sl;
        agg::path_storage path;
        path.move_to(8, 32.0);
        path.line_to(56, 32.0);
        agg::conv_stroke<agg::path_storage> stroke(path);
        stroke.width(2.0);
        renb.clear(agg::rgba8(0, 0, 0, 255));
        ras.add_path(stroke);
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(0, 255, 0, 255));
        // stroke centered on y=32 with width 2 → rows 31/32 fully covered
        check(pix(buf, W, 32, 32, CH_G) == 255, "line center row fully green");
        check(pix(buf, W, 16, 32, CH_G) == 255, "line interior pixel green");
        // far above the line: untouched
        check(pix(buf, W, 32, 8, CH_G) == 0, "row above line untouched");
    }

    // ── 3. anti-aliased triangle: interior solid, edge is blended ──
    memset(buf, 0, W * H * 4);
    {
        agg::rendering_buffer rb(buf, W, H, W * 4);
        agg::pixfmt_bgra32 pixf(rb);
        agg::renderer_base<agg::pixfmt_bgra32> renb(pixf);
        agg::rasterizer_scanline_aa<> ras;
        agg::scanline_p8 sl;
        ras.reset();
        ras.move_to_d(32.0, 8.0);
        ras.line_to_d(56.0, 56.0);
        ras.line_to_d(8.0, 56.0);
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(0, 0, 255, 255));
        // centroid: solid blue (B channel at offset 0)
        check(pix(buf, W, 32, 40, CH_B) == 255, "triangle centroid solid blue");
        check(pix(buf, W, 32, 40, CH_G) == 0,   "triangle centroid G==0");
        check(pix(buf, W, 32, 40, CH_A) == 255, "triangle centroid opaque");
        // apex row is thin: y=8 has partial coverage (cover 64 ≈ 25%)
        unsigned apex = pix(buf, W, 31, 8, CH_B);
        check(apex > 0 && apex < 255, "triangle apex row is anti-aliased");
    }

    // ── 4. blending: 50% red over black → R in [126,129] ──
    memset(buf, 0, W * H * 4);
    {
        agg::rendering_buffer rb(buf, W, H, W * 4);
        agg::pixfmt_bgra32 pixf(rb);
        agg::renderer_base<agg::pixfmt_bgra32> renb(pixf);
        agg::rasterizer_scanline_aa<> ras;
        agg::scanline_p8 sl;
        renb.clear(agg::rgba8(0, 0, 0, 255));
        ras.reset();
        ras.move_to_d(10.0, 10.0);
        ras.line_to_d(50.0, 10.0);
        ras.line_to_d(50.0, 30.0);
        ras.line_to_d(10.0, 30.0);
        // alpha=128 → destination ≈ 255*128/255 ≈ 127..128
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(255, 0, 0, 128));
        unsigned r = pix(buf, W, 30, 20, CH_R);
        check(r >= 126 && r <= 129, "50% alpha blend red in [126,129]");
        check(pix(buf, W, 30, 20, CH_A) == 255, "blended pixel stays opaque");
    }

    // ── 5. boundary / degenerate inputs must not crash ──
    {
        // zero-area polygon (all vertices identical)
        agg::rendering_buffer rb(buf, W, H, W * 4);
        agg::pixfmt_bgra32 pixf(rb);
        agg::renderer_base<agg::pixfmt_bgra32> renb(pixf);
        agg::rasterizer_scanline_aa<> ras;
        agg::scanline_p8 sl;
        ras.reset();
        ras.move_to_d(20.0, 20.0);
        ras.line_to_d(20.0, 20.0);
        ras.line_to_d(20.0, 20.0);
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(255, 255, 0, 255));
        check(true, "degenerate polygon renders without crash");

        // fully-outside-bounds polygon: buffer must stay untouched
        memset(buf, 0, W * H * 4);
        ras.reset();
        ras.move_to_d(200.0, 200.0);
        ras.line_to_d(300.0, 200.0);
        ras.line_to_d(300.0, 300.0);
        agg::render_scanlines_aa_solid(ras, sl, renb, agg::rgba8(255, 255, 0, 255));
        unsigned sum = 0;
        for (int i = 0; i < W * H * 4; i++) sum += buf[i];
        check(sum == 0, "off-canvas polygon writes nothing");

        // 1x1 rendering buffer: legal minimal surface. clear() writes
        // rgba8(r=9,g=8,b=7,a=6) as BGRA bytes {7,8,9,6}.
        unsigned char one[4] = {0, 0, 0, 0};
        agg::rendering_buffer rb1(one, 1, 1, 4);
        agg::pixfmt_bgra32 p1(rb1);
        agg::renderer_base<agg::pixfmt_bgra32> r1(p1);
        r1.clear(agg::rgba8(9, 8, 7, 6));
        check(one[CH_B] == 7 && one[CH_G] == 8 && one[CH_R] == 9 && one[CH_A] == 6,
              "1x1 buffer clear writes exact bytes");
    }

    delete[] buf;
    printf("libagg render checks: %d run, %d failed\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
