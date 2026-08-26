// Consumer test for libheinz 4.1.0 — exercises the three public headers
// (Complex.h, Vectors3D.h, Rotations3D.h) and checks return values.
//
// Assertion counting: every CHECK_* macro increments g_checks; a failed
// comparison increments g_failures.  The program exits non-zero if any
// assertion fails so CTest reports the failure.
#include <heinz/Complex.h>
#include <heinz/Rotations3D.h>
#include <heinz/Vectors3D.h>

#include <cmath>
#include <cstdio>

static int g_checks = 0;
static int g_failures = 0;

static void check_near(const char *file, int line, double actual,
                       double expected, double eps)
{
    ++g_checks;
    if (std::abs(actual - expected) > eps) {
        ++g_failures;
        std::fprintf(stderr, "FAIL [%s:%d]: expected %.15g, got %.15g\n",
                     file, line, expected, actual);
    }
}

static void check_true(const char *file, int line, bool cond)
{
    ++g_checks;
    if (!cond) {
        ++g_failures;
        std::fprintf(stderr, "FAIL [%s:%d]: condition false\n", file, line);
    }
}

#define CHECK_NEAR(actual, expected, eps) \
    check_near(__FILE__, __LINE__, (actual), (expected), (eps))
#define CHECK_TRUE(cond) check_true(__FILE__, __LINE__, (cond))

using RotMatrix = Rotation3D<double>;

static const double PI = 3.14159265358979323846;

int main()
{
    // ── Complex.h: complex_t, I, mul_I, exp_I, isfinite ──────────────
    complex_t z(3.0, 4.0);
    CHECK_NEAR(z.real(), 3.0, 1e-15);
    CHECK_NEAR(z.imag(), 4.0, 1e-15);

    // mul_I(z) = I*z = (-imag, real)
    CHECK_NEAR(mul_I(z).real(), -4.0, 1e-15);
    CHECK_NEAR(mul_I(z).imag(), 3.0, 1e-15);
    CHECK_NEAR(mul_I(complex_t(1.0, 0.0)).imag(), 1.0, 1e-15);

    // exp_I(z) = exp(I*z) = exp(-imag) * (cos(real) + I*sin(real))... actually
    // exp_I(z) = exp(complex_t(-z.imag(), z.real()))
    complex_t ei = exp_I(complex_t(0.0, 0.0));
    CHECK_NEAR(ei.real(), 1.0, 1e-15);
    CHECK_NEAR(ei.imag(), 0.0, 1e-15);

    CHECK_TRUE(isfinite(z));
    CHECK_TRUE(!isfinite(complex_t(std::numeric_limits<double>::infinity(), 0.0)));

    // ── Vectors3D.h: R3/C3/I3 construction, mag, dot, cross, arithmetic ──
    R3 v(1.0, 2.0, 3.0);
    CHECK_NEAR(v.x(), 1.0, 1e-15);
    CHECK_NEAR(v.y(), 2.0, 1e-15);
    CHECK_NEAR(v.z(), 3.0, 1e-15);
    CHECK_NEAR(v.mag2(), 14.0, 1e-15);
    CHECK_NEAR(v.mag(), std::sqrt(14.0), 1e-12);

    R3 a(1.0, 2.0, 3.0);
    R3 b(10.0, 20.0, 30.0);
    R3 sum = a + b;
    CHECK_NEAR(sum.x(), 11.0, 1e-15);
    CHECK_NEAR(sum.y(), 22.0, 1e-15);
    CHECK_NEAR(sum.z(), 33.0, 1e-15);

    R3 diff = b - a;
    CHECK_NEAR(diff.x(), 9.0, 1e-15);
    CHECK_NEAR(diff.y(), 18.0, 1e-15);
    CHECK_NEAR(diff.z(), 27.0, 1e-15);

    // dot product: 1*10 + 2*20 + 3*30 = 140
    CHECK_NEAR(a.dot(b), 140.0, 1e-12);

    // cross product: a x b = (a.y*b.z-a.z*b.y, a.z*b.x-a.x*b.z, a.x*b.y-a.y*b.x)
    R3 cr = a.cross(b);
    CHECK_NEAR(cr.x(), a.y() * b.z() - a.z() * b.y(), 1e-12);
    CHECK_NEAR(cr.y(), a.z() * b.x() - a.x() * b.z(), 1e-12);
    CHECK_NEAR(cr.z(), a.x() * b.y() - a.y() * b.x(), 1e-12);

    // scalar multiply
    R3 sm = 2.0 * a * 2.0;
    CHECK_NEAR(sm.x(), 4.0, 1e-15);
    CHECK_NEAR(sm.y(), 8.0, 1e-15);
    CHECK_NEAR(sm.z(), 12.0, 1e-15);

    // equality
    CHECK_TRUE(a == R3(1.0, 2.0, 3.0));
    CHECK_TRUE(a != R3(1.0, 1.0, 3.0));

    // complex vector C3: dot of real-valued complex vector
    C3 cv(complex_t(1.0, 0.0), complex_t(2.0, 0.0), complex_t(3.0, 0.0));
    CHECK_NEAR(cv.dot(cv).real(), 14.0, 1e-12);

    // ── Rotations3D.h: identity, AroundX/Y/Z, EulerZXZ, Inverse ──────
    RotMatrix r0;
    CHECK_TRUE(r0.isIdentity());

    // AroundX — x component of a vector is unchanged
    RotMatrix rX = RotMatrix::AroundX(PI / 6.0);
    CHECK_TRUE(rX.isXRotation());
    R3 vx(1.0, 0.0, 0.0);
    R3 vxr = rX.transformed(vx);
    CHECK_NEAR(vxr.x(), 1.0, 1e-12);

    // Forth-and-back: inverse rotation restores the original vector
    RotMatrix rXinv = rX.Inverse();
    R3 vback = rXinv.transformed(vxr);
    CHECK_NEAR(vback.x(), vx.x(), 1e-12);
    CHECK_NEAR(vback.y(), vx.y(), 1e-12);
    CHECK_NEAR(vback.z(), vx.z(), 1e-12);

    // AroundY: rotate (sqrt3/2, 2, 0.5) by 30° → (1, 2, 0)
    R3 vy(std::sqrt(3.0) / 2.0, 2.0, 0.5);
    RotMatrix rY = RotMatrix::AroundY(PI / 6.0);
    R3 vyr = rY.transformed(vy);
    CHECK_NEAR(vyr.x(), 1.0, 1e-9);
    CHECK_NEAR(vyr.y(), 2.0, 1e-15);
    CHECK_NEAR(vyr.z(), 0.0, 1e-9);

    // AroundZ: rotate (0.5, sqrt3/2, 2) by 30° → (0, 1, 2)
    R3 vz(0.5, std::sqrt(3.0) / 2.0, 2.0);
    RotMatrix rZ = RotMatrix::AroundZ(PI / 6.0);
    R3 vzr = rZ.transformed(vz);
    CHECK_NEAR(vzr.x(), 0.0, 1e-9);
    CHECK_NEAR(vzr.y(), 1.0, 1e-9);
    CHECK_NEAR(vzr.z(), 2.0, 1e-15);

    // EulerZXZ round-trip: build from angles, recover them
    const double w0 = PI / 5.0;
    const double w1 = PI / 7.0;
    const double w2 = PI / 11.0;
    RotMatrix mEul = RotMatrix::EulerZXZ(w0, w1, w2);
    auto angles = mEul.zxzEulerAngles();
    CHECK_NEAR(angles[0], w0, 1e-10);
    CHECK_NEAR(angles[1], w1, 1e-10);
    CHECK_NEAR(angles[2], w2, 1e-10);

    std::printf("libheinz consumer test: %d checks, %d failures\n",
                g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
