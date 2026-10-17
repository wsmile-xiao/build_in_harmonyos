// ceres 2.2.0 消费者测试 —— 真实使用 Ceres 的公共 API（非线性最小二乘求解）
//
// 设计原则：全部断言确定性、无文件/网络/设备依赖；既覆盖 C++ 模板 API（AutoDiff 代价函数、
// Jet），也覆盖真实数值求解结果（拟合 y=2x+1 必须收敛到 m≈2、c≈1）。
// 以 `add_test` 注册进 ctest，由 test_package 以 ctest --output-on-failure 执行。
#include <cmath>
#include <cstdio>
#include <string>

#include <ceres/ceres.h>
#include <ceres/manifold.h>
#include <ceres/rotation.h>
#include <ceres/version.h>

static int g_checks = 0;
static int g_fails = 0;

static void check(bool ok, const char* what) {
  ++g_checks;
  if (ok) {
    std::printf("PASS: %s\n", what);
  } else {
    ++g_fails;
    std::printf("FAIL: %s\n", what);
  }
}

// y = m*x + c 的残差（AutoDiff 自动求导）
struct LineResidual {
  LineResidual(double x, double y) : x_(x), y_(y) {}
  template <typename T>
  bool operator()(const T* const m, const T* const c, T* residual) const {
    residual[0] = T(y_) - (m[0] * T(x_) + c[0]);
    return true;
  }

 private:
  const double x_;
  const double y_;
};

int main() {
  // ── 1. 版本指纹 ────────────────────────────────────────────────
  check(std::string(CERES_VERSION_STRING).rfind("2.", 0) == 0,
        "CERES_VERSION_STRING 以 2. 开头（头文件可用）");

  // ── 2. Jet 自动微分基础设施 ────────────────────────────────────
  ceres::Jet<double, 1> j(3.0);
  j.v[0] = 1.0;                                  // d(3)/dx = 1
  const ceres::Jet<double, 1> jj = j * j + ceres::Jet<double, 1>(2.0);
  check(std::fabs(jj.a - 11.0) < 1e-12, "ceres::Jet 标量运算正确（3*3+2=11）");
  check(std::fabs(jj.v[0] - 6.0) < 1e-12, "ceres::Jet 导数传播正确（d/dx=6）");

  // ── 3. Problem 记账 API ───────────────────────────────────────
  const double xs[5] = {0.0, 1.0, 2.0, 3.0, 4.0};
  const double ys[5] = {1.0, 3.0, 5.0, 7.0, 9.0};   // 真值 m=2, c=1
  double m = 0.0;
  double c = 0.0;
  ceres::Problem problem;
  for (int i = 0; i < 5; ++i) {
    ceres::CostFunction* cost =
        new ceres::AutoDiffCostFunction<LineResidual, 1, 1, 1>(
            new LineResidual(xs[i], ys[i]));
    problem.AddResidualBlock(cost, nullptr, &m, &c);
  }
  check(problem.NumResidualBlocks() == 5, "Problem 残差块数 = 5");
  check(problem.NumParameterBlocks() == 2, "Problem 参数块数 = 2");
  check(problem.HasParameterBlock(&m), "HasParameterBlock(&m) 为真");
  check(problem.HasParameterBlock(&c), "HasParameterBlock(&c) 为真");

  // ── 4. 真实数值求解（DENSE_QR + 默认信赖域）────────────────────
  ceres::Solver::Options options;
  options.linear_solver_type = ceres::DENSE_QR;
  options.minimizer_progress_to_stdout = false;
  options.logging_type = ceres::SILENT;
  options.max_num_iterations = 50;
  ceres::Solver::Summary summary;
  ceres::Solve(options, &problem, &summary);

  check(summary.IsSolutionUsable(), "求解结果可用（IsSolutionUsable）");
  check(summary.termination_type == ceres::CONVERGENCE,
        "求解收敛（termination_type == CONVERGENCE）");
  check(std::fabs(m - 2.0) < 1e-8, "拟合斜率 m ≈ 2");
  check(std::fabs(c - 1.0) < 1e-8, "拟合截距 c ≈ 1");
  check(summary.final_cost < 1e-20, "最终代价 ≈ 0");
  check(summary.num_residual_blocks == 5, "Summary 记录 5 个残差块");

  // ── 5. rotation.h 实函数 ──────────────────────────────────────
  const double axis_angle[3] = {0.0, 0.0, M_PI / 2.0};   // 绕 z 轴 90°
  const double point[3] = {1.0, 0.0, 0.0};
  double rotated[3] = {0.0, 0.0, 0.0};
  ceres::AngleAxisRotatePoint(axis_angle, point, rotated);
  check(std::fabs(rotated[0]) < 1e-12 && std::fabs(rotated[1] - 1.0) < 1e-12,
        "AngleAxisRotatePoint：(1,0,0) 绕 z 轴 90° → (0,1,0)");

  // ── 6. Manifold 接口（2.x 公共 API）───────────────────────────
  ceres::Manifold* manifold = new ceres::EuclideanManifold<2>();
  check(manifold->AmbientSize() == 2 && manifold->TangentSize() == 2,
        "Manifold 接口可用（EuclideanManifold<2> 维度 2/2）");
  delete manifold;

  std::printf("\nchecks: %d  failures: %d\n", g_checks, g_fails);
  if (g_fails == 0) {
    std::printf("ALL PASS\n");
  }
  return g_fails == 0 ? 0 : 1;
}
