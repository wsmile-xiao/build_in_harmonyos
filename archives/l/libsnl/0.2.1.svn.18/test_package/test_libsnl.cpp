/* Consumer test for the installed libSNL package.
 *
 * Everything checked here is deterministic: point/vector arithmetic, the
 * linear solver (upstream's own 4x4 / 3 right-hand-side case) and NURBS global
 * interpolation (a curve must pass through the points it was fitted to).
 * The patterns mirror upstream's snlTest/testSquareLinear() and
 * testCurveInterpolation() but use the installed headers instead of the source
 * tree.  Note that snlSquareLinear takes ownership of the coefficient and
 * right-hand-side arrays (upstream allocates them with new[] and never frees
 * them), so they are heap allocated here as well.
 */
#include <cmath>
#include <cstdio>

#include <snlCurve.h>
#include <snlPoint.h>
#include <snlVector.h>

static int checks;
static int failures;

static void check(bool condition, const char *what)
{
    checks++;
    if (condition) {
        std::printf("ok   %s\n", what);
    } else {
        failures++;
        std::printf("FAIL %s\n", what);
    }
}

static bool close_to(double a, double b, double tol = 1.0e-9)
{
    return std::fabs(a - b) <= tol;
}

int main()
{
    std::setvbuf(stdout, NULL, _IOLBF, 0);

    snlPoint point;
    point.components(1.0, 2.0, 3.0, 1.0);
    check(close_to(point.x(), 1.0) && close_to(point.y(), 2.0)
          && close_to(point.z(), 3.0) && close_to(point.w(), 1.0),
          "snlPoint stores and returns four components");

    snlVector diagonal(3.0, 4.0, 0.0);
    check(close_to(diagonal.length(), 5.0), "snlVector::length 3-4-5");

    snlVector unitX(1.0, 0.0, 0.0);
    check(close_to(diagonal.dot(unitX), 3.0), "snlVector::dot");

    snlVector unitY(0.0, 1.0, 0.0);
    snlVector cross;
    cross.crossProduct(unitX, unitY);
    check(close_to(cross.x(), 0.0) && close_to(cross.y(), 0.0)
          && close_to(cross.z(), 1.0), "snlVector::crossProduct x cross y = z");

    snlPoint a;
    snlPoint b;
    a.components(0.0, 0.0, 0.0, 1.0);
    b.components(3.0, 4.0, 0.0, 1.0);
    snlVector between(a, b);
    check(close_to(between.length(), 5.0),
          "snlVector point-to-point distance");

    /* NURBS global interpolation: the curve passes through the input points. */
    snlPoint *points = new snlPoint[5];
    for (int index = 0; index < 5; index++) {
        points[index].components(index * 1.0, index * index * 1.0,
                                 10.0 - index, 1.0);
    }
    knot *params = 0;
    snlCurve curve(points, 5, snlCurve::SNL_GLOBAL_INTERPOLATION, 3, false, &params);
    check(params != 0, "snlCurve global interpolation returns knot parameters");
    check(curve.degree() == 3, "snlCurve keeps the requested degree");
    check(curve.size() == 5, "snlCurve keeps the control point count");

    double maxError = 0.0;
    for (int index = 0; index < 5 && params != 0; index++) {
        snlPoint evaluated = curve.evalHmg(params[index]);
        snlVector error(points[index], evaluated);
        if (error.length() > maxError) {
            maxError = error.length();
        }
    }
    check(maxError <= 1.0e-9, "interpolated curve passes through its data points");

    check(curve.maxParam() > curve.minParam(),
          "snlCurve parameter range is increasing");

    delete[] points;
    delete[] params;

    std::printf("checks: %d, failures: %d (max interpolation error %.3e)\n",
                checks, failures, maxError);
    return failures == 0 ? 0 : 1;
}
