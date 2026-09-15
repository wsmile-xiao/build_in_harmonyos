/* test_package/test.c — osqp/1.0.0 消费者测试（真实调用 OSQP 公共 API）
 *
 * 验证点（任一失败即非零退出）：
 *   1. osqp_version() 报告 1.0.0
 *   2. osqp_capabilities() 含内置直接求解器（QDLDL 已内联进本库）与代码生成能力
 *   3. 求解上游示例 QP，与解析最优解 x=[0.3, 0.7]、目标值 1.88 比对
 *   4. 数据更新（osqp_update_lin_cost）后重解，最优解按预期移动
 */
#include "osqp.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (cond) { printf("  [PASS] %s\n", msg); }                          \
        else      { printf("  [FAIL] %s\n", msg); failures++; }              \
    } while (0)

#define CHECK_NEAR(actual, expect, tol, msg)                                 \
    do {                                                                     \
        double _a = (double)(actual), _e = (double)(expect);                 \
        if (fabs(_a - _e) <= (tol)) {                                        \
            printf("  [PASS] %s (got %.8f, expect %.8f)\n", msg, _a, _e);    \
        } else {                                                             \
            printf("  [FAIL] %s (got %.8f, expect %.8f)\n", msg, _a, _e);    \
            failures++;                                                      \
        }                                                                    \
    } while (0)

/* 上游 examples/osqp_demo.c 的默认问题：
 *   minimize    1/2 x' P x + q' x
 *   subject to  l <= A x <= u
 *   P = [4 1; 1 2], q = [1, 1], A = [1 1; 1 0; 0 1], l = [1, 0, 0], u = [1, .7, .7]
 *   解析最优解 x* = [0.3, 0.7]，目标值 1.88
 */
int main(void) {
    OSQPFloat P_x[3] = {4.0, 1.0, 2.0};
    OSQPInt   P_i[3] = {0, 0, 1};
    OSQPInt   P_p[3] = {0, 1, 3};
    OSQPFloat q[2]   = {1.0, 1.0};
    OSQPFloat A_x[4] = {1.0, 1.0, 1.0, 1.0};
    OSQPInt   A_i[4] = {0, 1, 0, 2};
    OSQPInt   A_p[3] = {0, 2, 4};
    OSQPFloat l[3]   = {1.0, 0.0, 0.0};
    OSQPFloat u[3]   = {1.0, 0.7, 0.7};
    const OSQPInt n = 2, m = 3;

    OSQPInt exitflag;
    OSQPSolver*   solver   = NULL;
    OSQPSettings* settings = NULL;
    OSQPCscMatrix* P       = NULL;
    OSQPCscMatrix* A       = NULL;

    printf("osqp test_package: linked against libosqp %s\n", osqp_version());
    CHECK(strcmp(osqp_version(), "1.0.0") == 0, "osqp_version() == 1.0.0");

    OSQPInt cap = osqp_capabilities();
    CHECK((cap & OSQP_CAPABILITY_DIRECT_SOLVER) != 0,
          "capability: 内置直接线性求解器（QDLDL 已内联）");
    CHECK((cap & OSQP_CAPABILITY_CODEGEN) != 0,
          "capability: 代码生成已启用");

    P = OSQPCscMatrix_new(n, n, 3, P_x, P_i, P_p);
    A = OSQPCscMatrix_new(m, n, 4, A_x, A_i, A_p);
    settings = OSQPSettings_new();
    if (!P || !A || !settings) {
        printf("  [FAIL] 对象分配失败\n");
        return 1;
    }
    settings->verbose   = 0;
    settings->polishing = 1;
    settings->rho       = 1.0;
    settings->adaptive_rho = OSQP_ADAPTIVE_RHO_UPDATE_DISABLED;
    settings->eps_abs   = 1e-8;
    settings->eps_rel   = 1e-8;
    settings->max_iter  = 4000;

    exitflag = osqp_setup(&solver, P, q, A, l, u, m, n, settings);
    CHECK(exitflag == 0, "osqp_setup() 成功");
    if (exitflag != 0 || !solver) return 1;

    exitflag = osqp_solve(solver);
    CHECK(exitflag == 0, "osqp_solve() 成功");
    CHECK(solver->info->status_val == OSQP_SOLVED, "状态 == OSQP_SOLVED");
    printf("  状态字符串: %s, 迭代 %d 次\n",
           solver->info->status, (int)solver->info->iter);

    CHECK_NEAR(solver->solution->x[0], 0.3,  1e-5, "x[0] == 0.3");
    CHECK_NEAR(solver->solution->x[1], 0.7,  1e-5, "x[1] == 0.7");
    CHECK_NEAR(solver->info->obj_val,  1.88, 1e-5, "目标值 == 1.88");

    /* 数据更新后重解：q -> [1, 2]，此时 x2 <= 0.7 不再起作用，
     * 无约束（在等式 x1+x2=1 上）最优为 x* = [0.5, 0.5]，目标值 2.5 */
    OSQPFloat q2[2] = {1.0, 2.0};
    exitflag = osqp_update_data_vec(solver, q2, NULL, NULL);
    CHECK(exitflag == 0, "osqp_update_data_vec() 成功");
    exitflag = osqp_solve(solver);
    CHECK(exitflag == 0, "更新后 osqp_solve() 成功");
    CHECK_NEAR(solver->solution->x[0], 0.5, 1e-5, "更新后 x[0] == 0.5");
    CHECK_NEAR(solver->solution->x[1], 0.5, 1e-5, "更新后 x[1] == 0.5");

    osqp_cleanup(solver);
    OSQPCscMatrix_free(P);
    OSQPCscMatrix_free(A);
    OSQPSettings_free(settings);

    if (failures) {
        printf("osqp test_package: %d 项断言失败\n", failures);
        return 1;
    }
    printf("osqp test_package: 全部断言通过\n");
    return 0;
}
