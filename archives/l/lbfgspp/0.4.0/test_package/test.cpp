/* test_package/test.cpp — LBFGS++ 0.4.0 consumer optimization test
 *
 * Real optimization convergence tests (NOT just class instantiation):
 *   1. Rosenbrock function: n=10, x0=zeros (non-optimal start) → x→[1,1,...], f(x)→0
 *   2. Quadratic function: f(x) = ||x-d||^2, x0=zeros → x→d=[0,1,...,9], f(x)→0
 *   3. Gradient norm check: ||grad|| < epsilon after convergence
 *
 * Each test verifies the solver converged to the known optimum within tolerance.
 */
#include <Eigen/Core>
#include <LBFGS.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>

using Eigen::VectorXd;
using namespace LBFGSpp;

// ── Test 1: Rosenbrock function (classic non-convex test) ──
// f(x) = sum_{i=0,2,...} [ (1-x_i)^2 + 100*(x_{i+1}-x_i^2)^2 ]
// Optimum: x = [1, 1, ..., 1], f(x) = 0
class Rosenbrock
{
private:
    int n;
public:
    explicit Rosenbrock(int n_) : n(n_) {}
    double operator()(const VectorXd& x, VectorXd& grad)
    {
        double fx = 0.0;
        for (int i = 0; i < n; i += 2)
        {
            double t1 = 1.0 - x[i];
            double t2 = 10.0 * (x[i + 1] - x[i] * x[i]);
            grad[i + 1] = 20.0 * t2;
            grad[i]     = -2.0 * (x[i] * grad[i + 1] + t1);
            fx += t1 * t1 + t2 * t2;
        }
        return fx;
    }
};

static int test_rosenbrock()
{
    const int n = 10;
    LBFGSParam<double> param;
    param.epsilon = 1e-6;
    param.max_iterations = 200;

    LBFGSSolver<double> solver(param);
    Rosenbrock fun(n);

    // Non-optimal initial guess: all zeros (Rosenbrock minimum is at all-ones)
    VectorXd x = VectorXd::Zero(n);
    double fx;
    int niter = solver.minimize(fun, x, fx);

    printf("[rosenbrock] iterations=%d\n", niter);
    printf("[rosenbrock] f(x) = %.6e (expect ~0)\n", fx);

    // Verify convergence: f(x) should be near 0
    double tol = 1e-4;
    int errors = 0;

    if (fx > tol) {
        fprintf(stderr, "[FAIL] Rosenbrock: f(x)=%.6e exceeds tolerance %.1e\n", fx, tol);
        errors++;
    }

    // Verify x converged to [1,1,...,1]
    for (int i = 0; i < n; i++) {
        if (std::abs(x[i] - 1.0) > 1e-3) {
            fprintf(stderr, "[FAIL] Rosenbrock: x[%d]=%.6f expected 1.0 (tol 1e-3)\n", i, x[i]);
            errors++;
            break;
        }
    }

    // Verify gradient norm is small (convergence indicator)
    double gnorm = solver.final_grad_norm();
    printf("[rosenbrock] ||grad|| = %.6e (expect < %g)\n", gnorm, param.epsilon);
    if (gnorm > param.epsilon * 10.0) {
        fprintf(stderr, "[FAIL] Rosenbrock: ||grad||=%.6e exceeds 10*epsilon=%g\n",
                gnorm, param.epsilon * 10.0);
        errors++;
    }

    if (errors == 0)
        printf("[PASS] Rosenbrock convergence verified (x->1, f->0, ||grad|| small)\n");
    return errors;
}

// ── Test 2: Simple quadratic function ──
// f(x) = ||x - d||^2 where d = [0, 1, 2, ..., 9]
// Optimum: x = d, f(x) = 0, grad = 0
class Quadratic
{
private:
    int n;
public:
    explicit Quadratic(int n_) : n(n_) {}
    double operator()(const VectorXd& x, VectorXd& grad)
    {
        VectorXd d(n);
        for (int i = 0; i < n; i++)
            d[i] = static_cast<double>(i);

        double f = (x - d).squaredNorm();
        grad.noalias() = 2.0 * (x - d);
        return f;
    }
};

static int test_quadratic()
{
    const int n = 10;
    LBFGSParam<double> param;
    param.epsilon = 1e-8;
    param.max_iterations = 100;

    LBFGSSolver<double> solver(param);
    Quadratic fun(n);

    // Non-optimal initial guess: all zeros (optimum is at [0,1,...,9])
    VectorXd x = VectorXd::Zero(n);
    double fx;
    int niter = solver.minimize(fun, x, fx);

    printf("[quadratic] iterations=%d\n", niter);
    printf("[quadratic] f(x) = %.6e (expect ~0)\n", fx);

    int errors = 0;
    double tol = 1e-10;

    if (fx > tol) {
        fprintf(stderr, "[FAIL] Quadratic: f(x)=%.6e exceeds tolerance %.1e\n", fx, tol);
        errors++;
    }

    // Verify x converged to [0,1,2,...,9]
    for (int i = 0; i < n; i++) {
        if (std::abs(x[i] - static_cast<double>(i)) > 1e-4) {
            fprintf(stderr, "[FAIL] Quadratic: x[%d]=%.6f expected %d (tol 1e-4)\n", i, x[i], i);
            errors++;
            break;
        }
    }

    if (errors == 0)
        printf("[PASS] Quadratic convergence verified (x->d, f->0)\n");
    return errors;
}

int main()
{
    printf("=== LBFGS++ 0.4.0 Optimization Tests ===\n\n");

    int total_errors = 0;

    printf("--- Test 1: Rosenbrock function (n=10) ---\n");
    total_errors += test_rosenbrock();
    printf("\n");

    printf("--- Test 2: Quadratic function (n=10) ---\n");
    total_errors += test_quadratic();
    printf("\n");

    if (total_errors == 0) {
        printf("=== ALL TESTS PASSED ===\n");
        printf("Total: 2  Pass: 2  Fail: 0  Skip: 0\n");
        return 0;
    } else {
        printf("=== TESTS FAILED ===\n");
        printf("Total: 2  Pass: %d  Fail: %d  Skip: 0\n",
               2 - total_errors, total_errors);
        return 1;
    }
}
