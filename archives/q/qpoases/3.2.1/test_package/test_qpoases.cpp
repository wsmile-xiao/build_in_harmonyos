/*
 * Consumer end-to-end test for the OHOS qpOASES 3.2.1 package.
 *
 * This is a real consumer of the installed package: it includes only the public
 * header exported by the package (<qpOASES.hpp>) and links against the packaged
 * static library, exactly as a downstream application would.  It solves QPs and
 * checks the results against values that are verified analytically below (and
 * that are identical, bit for bit, to the native x86_64 build of the same code).
 *
 * QP 1 (the canonical problem of the upstream examples/example1.cpp)
 * -----------------------------------------------------------------
 *   min  1/2 x'Hx + g'x ,  H = diag(1, 0.5), g = (1.5, 1)
 *   s.t. 0.5 <= x1 <= 5 ,  -2 <= x2 <= 2 ,  -1 <= x1 + x2 <= 2
 *
 *   Solution x* = (0.5, -1.5), objective -0.0625.
 *   Hand check: x1 sits at its lower bound 0.5 and the constraint
 *   x1 + x2 = -1 is active (x2 = -1.5).  Stationarity of the Lagrangian
 *   requires H x + g = (x1 + 1.5, 0.5 x2 + 1) = (2, 0.25), which matches the
 *   dual solution y = (1.75, 0, 0.25).
 *   Objective: 0.5*0.5^2 + 0.5*0.5*(-1.5)^2 + 1.5*0.5 + 1*(-1.5)
 *            = 0.125 + 0.5625 + 0.75 - 1.5 = -0.0625.
 *
 * QP 2 (hot-start of QP 1 through the SQProblem API)
 * --------------------------------------------------
 *   Same H and A, with g = (1, 1.5), bounds 0 <= x1 <= 5, -1 <= x2 <= -0.5 and
 *   constraint -2 <= x1 + x2 <= 1.  Solution x* = (0, -1), objective -1.25.
 *   Hand check: x1 = 0 and x2 = -1 both sit at their lower bounds; the
 *   inequality constraint is inactive (-1 is inside [-2, 1]).
 *   Objective: 0.5*0^2 + 0.5*0.5*(-1)^2 + 1*0 + 1.5*(-1) = 0.25 - 1.5 = -1.25.
 */
#include <cmath>
#include <cstdio>

#include <qpOASES.hpp>

USING_NAMESPACE_QPOASES

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const char *what)
{
    ++g_checks;
    if (!ok) {
        ++g_failures;
        std::printf("  FAIL  %s\n", what);
    } else {
        std::printf("  ok    %s\n", what);
    }
}

static bool near(real_t a, real_t b, real_t tol) { return std::fabs(a - b) <= tol; }

int main()
{
    std::printf("qpOASES consumer end-to-end test (OHOS aarch64)\n");

    /* ---- Problem data of the upstream example1 QP ---------------------- */
    real_t H[2 * 2] = { 1.0, 0.0, 0.0, 0.5 };
    real_t A[1 * 2] = { 1.0, 1.0 };
    real_t g[2]     = { 1.5, 1.0 };
    real_t lb[2]    = { 0.5, -2.0 };
    real_t ub[2]    = { 5.0, 2.0 };
    real_t lbA[1]   = { -1.0 };
    real_t ubA[1]   = { 2.0 };

    /* ---- QP 1: solve with the dense QProblem interface ----------------- */
    QProblem qp(2, 1);
    Options opts;
    opts.setToDefault();
    opts.printLevel = PL_NONE;
    qp.setOptions(opts);

    int_t nWSR = 10;
    returnValue rv = qp.init(H, g, A, lb, ub, lbA, ubA, nWSR);
    check(rv == SUCCESSFUL_RETURN, "QProblem::init returned SUCCESSFUL_RETURN");

    real_t xOpt[2];
    rv = qp.getPrimalSolution(xOpt);
    check(rv == SUCCESSFUL_RETURN, "QProblem::getPrimalSolution returned SUCCESSFUL_RETURN");

    real_t yOpt[3];
    rv = qp.getDualSolution(yOpt);
    check(rv == SUCCESSFUL_RETURN, "QProblem::getDualSolution returned SUCCESSFUL_RETURN");

    /* Primal solution: x1 at its lower bound, x2 = -1.5, so x1 + x2 = -1
     * exactly at the lower limit of the inequality constraint. */
    check(near(xOpt[0], 0.5, 1e-9) && near(xOpt[1], -1.5, 1e-9),
          "QP1 primal solution is x* = (0.5, -1.5) as derived analytically");
    check(near(xOpt[0] + xOpt[1], -1.0, 1e-9),
          "QP1 active constraint x1 + x2 = -1 holds at the solution");
    check(xOpt[0] >= lb[0] - 1e-9 && xOpt[0] <= ub[0] + 1e-9 &&
          xOpt[1] >= lb[1] - 1e-9 && xOpt[1] <= ub[1] + 1e-9,
          "QP1 primal solution respects all variable bounds");
    check(near(yOpt[0], 1.75, 1e-9) && near(yOpt[2], 0.25, 1e-9),
          "QP1 dual solution reproduces the analytic multipliers (1.75, 0, 0.25)");
    check(near(qp.getObjVal(), -0.0625, 1e-9),
          "QP1 objective equals the analytic minimum -0.0625");

    /* ---- QP 2: hot-started re-solve through SQProblem ------------------ */
    real_t g_new[2]   = { 1.0, 1.5 };
    real_t lb_new[2]  = { 0.0, -1.0 };
    real_t ub_new[2]  = { 5.0, -0.5 };
    real_t lbA_new[1] = { -2.0 };
    real_t ubA_new[1] = { 1.0 };

    SQProblem sqp(2, 1);
    sqp.setOptions(opts);
    int_t nWSR2 = 10;
    rv = sqp.init(H, g, A, lb, ub, lbA, ubA, nWSR2);
    check(rv == SUCCESSFUL_RETURN, "SQProblem::init returned SUCCESSFUL_RETURN");

    int_t nWSR3 = 10;
    rv = sqp.hotstart(g_new, lb_new, ub_new, lbA_new, ubA_new, nWSR3);
    check(rv == SUCCESSFUL_RETURN, "SQProblem::hotstart returned SUCCESSFUL_RETURN");

    real_t x2[2];
    sqp.getPrimalSolution(x2);
    check(near(x2[0], 0.0, 1e-9) && near(x2[1], -1.0, 1e-9),
          "QP2 hot-started solution is x* = (0, -1) as derived analytically");
    check(near(sqp.getObjVal(), -1.25, 1e-9),
          "QP2 objective equals the analytic minimum -1.25");

    /* A hot-started SQProblem must still expose a usable working set. */
    real_t wsB[2];
    rv = sqp.getWorkingSetBounds(wsB);
    check(rv == SUCCESSFUL_RETURN,
          "QP2 getWorkingSetBounds returned SUCCESSFUL_RETURN");

    /* ---- Utility surface of the packaged library ----------------------- */
    real_t v[4] = { 1.0, 2.0, 3.0, 4.0 };
    check(near(getNorm(v, 4), std::sqrt(30.0), 1e-9),
          "getNorm over {1,2,3,4} equals sqrt(30)");

    std::printf("\nchecks: %d, failures: %d\n", g_checks, g_failures);
    if (g_failures == 0) {
        std::printf("ALL CONSUMER CHECKS PASSED\n");
        return 0;
    }
    std::printf("CONSUMER CHECKS FAILED\n");
    return 1;
}
