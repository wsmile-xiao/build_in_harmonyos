// HarmonyOS-specific consumer test: verify the packaged library on the OHOS
// platform — static-linking path (all liboglappth GL/GLU symbols resolve
// through gl4es), OHOS math library (sqrt/acos in libm.so), and the vector
// templates with libc++-ohos types.
#include <oglv3d.h>
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
    // 1. The library loads and its object-location chain works on OHOS.
    ogl_ol_static loc;
    ogl_object_location * copy = loc.MakeCopy();
    CHECK(copy != NULL, "ogl_ol_static::MakeCopy non-null");
    delete copy;

    // 2. OHOS libm: len() uses sqrt via the platform math library.
    oglv3d<GLfloat> v(1.0f, 1.0f, 1.0f);
    CHECK(std::fabs(v.len() - std::sqrt(3.0f)) < 1e-5f, "sqrt path via OHOS libm");

    // 3. Vector ops with libc++-ohos: chained arithmetic on the template.
    oglv3d<GLfloat> a(1.0f, 2.0f, 3.0f);
    oglv3d<GLfloat> b(4.0f, 5.0f, 6.0f);
    oglv3d<GLfloat> s = a + b;
    oglv3d<GLfloat> p = a * 2.0f;
    CHECK(s.data[0] == 5.0f && s.data[1] == 7.0f && s.data[2] == 9.0f,
          "operator+ chain");
    CHECK(p.data[0] == 2.0f && p.data[1] == 4.0f && p.data[2] == 6.0f,
          "operator* scalar");

    // 4. ang() exercises acos — precision contract on the OHOS toolchain.
    oglv3d<GLfloat> e1(1.0f, 0.0f, 0.0f);
    CHECK(std::fabs(e1.ang(e1)) < 1e-6f, "ang self zero");
    CHECK(std::fabs(e1.ang(a) - std::acos(1.0f / std::sqrt(14.0f))) < 1e-5f,
          "acos precision");

    std::printf("%d/%d assertions passed\n", g_pass, g_total);
    return (g_pass == g_total) ? 0 : 1;
}
