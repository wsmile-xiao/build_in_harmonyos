// Consumer test for liboglappth 1.0.0 — real public-API assertions, no GL
// context needed. Exercises: oglv3d vector math (len/spr/vpr/operator-) and
// ogl_camera::CopySettings through the ogl_ol_static default-constructible
// location chain.
#include <oglv3d.h>
#include <ogl_camera.h>
#include <ogl_objects.h>

#include <cmath>
#include <cstdio>

static int g_pass = 0;
static int g_total = 0;

#define CHECK(cond, name)                                                     \
    do {                                                                      \
        ++g_total;                                                            \
        if (cond) { ++g_pass; std::printf("PASS: %s\n", name); }              \
        else      { std::printf("FAIL: %s\n", name); }                        \
    } while (0)

int main(void)
{
    // ── oglv3d: constructor from components ──
    oglv3d<GLfloat> v(3.0f, 4.0f, 0.0f);
    CHECK(v.data[0] == 3.0f && v.data[1] == 4.0f && v.data[2] == 0.0f,
          "oglv3d component constructor");

    // ── oglv3d::len — 3-4-5 triangle ──
    CHECK(std::fabs(v.len() - 5.0f) < 1e-5f, "oglv3d::len");

    // ── oglv3d::spr (dot product) — orthogonal vectors ──
    oglv3d<GLfloat> e1(1.0f, 0.0f, 0.0f);
    oglv3d<GLfloat> e2(0.0f, 1.0f, 0.0f);
    CHECK(std::fabs(e1.spr(e2)) < 1e-6f, "oglv3d::spr orthogonal");
    CHECK(std::fabs(e1.spr(e1) - 1.0f) < 1e-6f, "oglv3d::spr self");

    // ── oglv3d::vpr (cross product) — e1 x e2 = e3 ──
    oglv3d<GLfloat> e3 = e1.vpr(e2);
    CHECK(e3.data[0] == 0.0f && e3.data[1] == 0.0f && e3.data[2] == 1.0f,
          "oglv3d::vpr e1 x e2 = e3");

    // ── oglv3d::operator- and operator* ──
    oglv3d<GLfloat> d = v - e1 * 3.0f;
    CHECK(d.data[0] == 0.0f && d.data[1] == 4.0f && d.data[2] == 0.0f,
          "oglv3d operator- / operator*");

    // ── oglv3d::ang — angle between e1 and e2 is 90 degrees ──
    CHECK(std::fabs(e1.ang(e2) - M_PI / 2.0f) < 1e-5f, "oglv3d::ang 90deg");

    // ── ogl_camera: construct with a static location, then CopySettings ──
    ogl_ol_static loc1;
    ogl_ol_static loc2;
    ogl_camera cam1(loc1, 2.5f);
    ogl_camera cam2(loc2, 1.0f);

    // defaults set by the constructor
    CHECK(cam2.focus == 1.0f, "ogl_camera constructor focus");
    CHECK(cam2.clipping == 0.90f, "ogl_camera constructor clipping");
    CHECK(cam2.stereo_mode == false && cam2.ortho == false,
          "ogl_camera constructor flags");

    // perturb cam2, then copy cam1's settings over
    cam2.focus = 9.0f;
    cam2.clipping = 0.5f;
    cam2.GetLD()->crd[0] = 7.0f;
    cam2.GetLD()->zdir = oglv3d<GLfloat>(0.0f, 0.0f, 1.0f);

    bool ok = cam2.CopySettings(&cam1);
    CHECK(ok, "ogl_camera::CopySettings returns true");
    CHECK(cam2.focus == cam1.focus && cam2.focus == 2.5f, "CopySettings focus");
    CHECK(cam2.clipping == cam1.clipping && cam2.clipping == 0.90f,
          "CopySettings clipping");
    CHECK(cam2.GetLD()->crd[0] == 0.0f, "CopySettings crd copied");
    CHECK(cam2.GetLD()->zdir.data[2] == 1.0f && cam2.GetLD()->zdir.data[0] == 0.0f,
          "CopySettings zdir copied");

    // CopySettings from a non-static location must fail: use a second camera
    // whose location is a copy (still ogl_ol_static) — verify the dynamic_cast
    // positive path twice, then the negative path via self-made derived trick
    // is not possible without subclassing; the API contract (false on
    // non-static) is upstream-documented, cover the positive contract here.
    CHECK(cam2.CopySettings(&cam1) == true, "CopySettings repeatable");

    std::printf("%d/%d assertions passed\n", g_pass, g_total);
    return (g_pass == g_total) ? 0 : 1;
}
