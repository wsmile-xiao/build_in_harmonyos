#include <cmath>
#include <cstdio>
#include "cppoptlib/meta.h"
#include "cppoptlib/problem.h"
#include "cppoptlib/solver/bfgssolver.h"

using namespace cppoptlib;

// 经典 Rosenbrock：最小值 f(1,1)=0
class Rosenbrock : public Problem<double, 2> {
  public:
    double value(const TVector &x) override {
        const double t1 = 1 - x[0], t2 = x[1] - x[0] * x[0];
        return t1 * t1 + 100 * t2 * t2;
    }
    void gradient(const TVector &x, TVector &grad) override {
        grad[0] = -2 * (1 - x[0]) - 400 * x[0] * (x[1] - x[0] * x[0]);
        grad[1] = 200 * (x[1] - x[0] * x[0]);
    }
};

int main() {
    Rosenbrock f;
    Rosenbrock::TVector x; x << -1.0, 2.0;
    BfgsSolver<Rosenbrock> solver;
    solver.minimize(f, x);
    printf("min f=%.6g at (%.6f, %.6f)\n", f(x), x[0], x[1]);
    if (std::fabs(f(x)) > 1e-4 || std::fabs(x[0] - 1) > 1e-2 || std::fabs(x[1] - 1) > 1e-2) {
        printf("FAIL: BFGS did not converge to (1,1)\n");
        return 1;
    }
    printf("PASS: BFGS converged to Rosenbrock minimum on HarmonyOS\n");
    return 0;
}
