// Consumer test for the tasmanian Conan package.
//
// The upstream tester sources are an in-tree regression suite; they do not
// verify that a third party can install the package, include the public
// headers, link the static archives and run the public API. This file covers
// that consumer contract:
//   1. Clenshaw-Curtis level grid: quadrature weights, integral value and
//      convergence between two levels (upstream example 1),
//   2. Gauss-Patterson total degree grid on a transformed domain
//      (upstream example 2),
//   3. local polynomial interpolant: loading model values and evaluating,
//   4. the C interface header must be installed and linkable.
//
// Reference values and the expected error magnitudes come from the upstream
// example program (SparseGrids/Examples/example_sparse_grids_01.cpp and
// _02.cpp) run on the HarmonyOS PC with these very settings:
//   CC level 6 -> error 8.6e-12, CC level 7 -> error 1.8e-15,
//   Gauss-Patterson exactness 40 on [-5,5]x[-2,3] -> error 7.2e-11.

#include "Tasmanian.hpp"          // C++ public header (TasGrid::TasmanianSparseGrid)
#include "TasmanianSparseGrid.h"  // C interface public header

#include <cmath>
#include <cstdio>
#include <vector>

static int checks = 0;
static int failures = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        ++checks;                                                          \
        if (!(cond)) {                                                     \
            ++failures;                                                    \
            std::printf("FAIL line %d: %s\n", __LINE__, #cond);            \
        }                                                                  \
    } while (0)

// Integral of exp(-x^2) * cos(y) over the grid domain, using the quadrature
// weights of a grid with no model values (upstream example 1 / 2 pattern).
static double integrate_exp_cos(TasGrid::TasmanianSparseGrid const &grid) {
    const int dim = grid.getNumDimensions();
    std::vector<double> points = grid.getPoints();
    std::vector<double> weights = grid.getQuadratureWeights();
    double value = 0.0;
    for (int i = 0; i < grid.getNumPoints(); ++i) {
        const double x = points[i * dim];
        const double y = points[i * dim + 1];
        value += weights[i] * std::exp(-x * x) * std::cos(y);
    }
    return value;
}

int main() {
    const double exact = 2.513723354063905e+00;

    // ---- 1. Clenshaw-Curtis level grid (upstream example 1) --------------
    TasGrid::TasmanianSparseGrid coarse;
    CHECK(coarse.getNumDimensions() == 0);  // empty grid before construction

    coarse.makeGlobalGrid(2, 0, 6, TasGrid::type_level, TasGrid::rule_clenshawcurtis);
    CHECK(coarse.getNumDimensions() == 2);
    CHECK(coarse.getNumPoints() == 321);
    std::vector<double> points = coarse.getPoints();
    std::vector<double> weights = coarse.getQuadratureWeights();
    CHECK(points.size() == static_cast<std::size_t>(coarse.getNumPoints()) * 2);
    CHECK(weights.size() == static_cast<std::size_t>(coarse.getNumPoints()));

    const double error_coarse = std::fabs(integrate_exp_cos(coarse) - exact);
    CHECK(error_coarse < 1.0e-10);

    TasGrid::TasmanianSparseGrid fine;
    fine.makeGlobalGrid(2, 0, 7, TasGrid::type_level, TasGrid::rule_clenshawcurtis);
    CHECK(fine.getNumPoints() == 705);
    const double error_fine = std::fabs(integrate_exp_cos(fine) - exact);
    CHECK(error_fine < error_coarse);  // refinement must reduce the error
    CHECK(error_fine < 1.0e-13);

    // ---- 2. total degree quadrature on a transformed domain --------------
    // (upstream example 2: exactness 40 over [-5,5] x [-2,3])
    TasGrid::TasmanianSparseGrid transformed;
    transformed.makeGlobalGrid(2, 0, 40, TasGrid::type_qptotal, TasGrid::rule_gausspatterson);
    transformed.setDomainTransform({-5.0, -2.0}, {5.0, 3.0});
    const int num_points = transformed.getNumPoints();
    CHECK(num_points == 705);

    points = transformed.getPoints();
    weights = transformed.getQuadratureWeights();
    bool inside = true;
    for (int i = 0; i < num_points; ++i) {
        const double x = points[i * 2];
        const double y = points[i * 2 + 1];
        if (x < -5.0 || x > 5.0 || y < -2.0 || y > 3.0) {
            inside = false;
        }
    }
    CHECK(inside);

    const double error_transformed =
        std::fabs(integrate_exp_cos(transformed) - 1.861816427518323e+00);
    CHECK(error_transformed < 1.0e-9);

    // ---- 3. local polynomial interpolation ------------------------------
    TasGrid::TasmanianSparseGrid local;
    local.makeLocalPolynomialGrid(2, 1, 3);
    CHECK(local.getNumDimensions() == 2);
    CHECK(local.getNumOutputs() == 1);
    CHECK(local.getNumLoaded() == 0);
    CHECK(local.getNumNeeded() > 0);

    const int needed = local.getNumNeeded();
    std::vector<double> needed_points = local.getNeededPoints();
    CHECK(needed_points.size() == static_cast<std::size_t>(needed) * 2);

    std::vector<double> values(needed);
    for (int i = 0; i < needed; ++i) {
        const double x = needed_points[i * 2];
        const double y = needed_points[i * 2 + 1];
        values[i] = 2.0 * x + 3.0 * y + 1.0;  // linear: reproduced exactly
    }
    local.loadNeededPoints(values);
    CHECK(local.getNumLoaded() == needed);

    std::vector<double> xq = {0.31, -0.27};
    std::vector<double> yq;
    local.evaluate(xq, yq);
    CHECK(yq.size() == 1);
    CHECK(std::fabs(yq[0] - (2.0 * xq[0] + 3.0 * xq[1] + 1.0)) < 1.0e-12);

    // ---- 4. C interface header is installed and linkable -----------------
    void (*make_global)(void *, int, int, int, const char *, const char *,
                        const int *, double, double, const char *, const int *) =
        &tsgMakeGlobalGrid;
    CHECK(make_global != nullptr);

    if (failures == 0) {
        std::printf("TASMANIAN_CONSUMER_CHECKS=%d FAILURES=0\n", checks);
        std::printf("TASMANIAN_CONSUMER_OK\n");
    } else {
        std::printf("TASMANIAN_CONSUMER_CHECKS=%d FAILURES=%d\n", checks, failures);
    }
    return failures == 0 ? 0 : 1;
}
