// HarmonyOS 专项消费者验证 — cppnumericalsolvers 2.0.0
//
// 模拟业务上层组件：仅通过本库安装/导出的公开头文件
// (include/cppoptlib/...) 与公开 API 使用 cppnumericalsolvers，
// 不含库私有头文件、不调用内部符号、不复用库内部测试构建目录。
//
// 覆盖两个有业务意义的公开 API 调用及其可观察结果：
//   1. cppoptlib::function::FunctionX2 / FunctionX2_dx（Rosenbrock 目标函数）
//   2. cppoptlib::solver::Lbfgs::Minimize（L-BFGS 求解器）
// 并断言收敛结果 f(1,1)=0 的数值可观察。

#include <cmath>
#include <cstdio>

#include "cppoptlib/function.h"
#include "cppoptlib/solver/lbfgs.h"

// 经典 Rosenbrock（值 + 梯度，2.0.0 公开 CRTP 接口 FunctionXd<F>）：
// 最小值 f(1,1)=0。FunctionXd = FunctionCRTP<F, double, First>，
// 只依赖库公开头文件 include/cppoptlib/function.h。
class Rosenbrock : public cppoptlib::function::FunctionXd<Rosenbrock> {
 public:
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  using typename cppoptlib::function::FunctionXd<Rosenbrock>::ScalarType;
  using typename cppoptlib::function::FunctionXd<Rosenbrock>::VectorType;

  ScalarType operator()(const VectorType& x,
                        VectorType* gradient = nullptr) const {
    const ScalarType t1 = (1 - x[0]);
    const ScalarType t2 = (x[1] - x[0] * x[0]);
    if (gradient) {
      *gradient = VectorType::Zero(2);
      (*gradient)[0] =
          -2 * (1 - x[0]) + 200 * (x[1] - x[0] * x[0]) * (-2 * x[0]);
      (*gradient)[1] = 200 * (x[1] - x[0] * x[0]);
    }
    return t1 * t1 + 100 * t2 * t2;
  }
};

int main() {
  using Function = Rosenbrock;
  using Solver = cppoptlib::solver::Lbfgs<Function>;

  Function f;
  Function::VectorType x(2);
  x << -1.0, 2.0;  // 远离极小点的起点 (1,1)

  // 公开 API 1：FunctionState 初始化
  auto initial_state = cppoptlib::function::FunctionState(x);

  // 公开 API 2：L-BFGS 求解
  Solver solver;
  auto [solution, solver_state] = solver.Minimize(f, initial_state);

  const double fx = f(solution.x);
  std::printf("min f=%.6g at (%.6f, %.6f) status=%d\n", fx, solution.x[0],
              solution.x[1], static_cast<int>(solver_state.status));
  std::fflush(stdout);

  if (std::fabs(fx) > 1e-4 || std::fabs(solution.x[0] - 1) > 1e-2 ||
      std::fabs(solution.x[1] - 1) > 1e-2) {
    std::printf("FAIL: L-BFGS did not converge to Rosenbrock minimum (1,1)\n");
    return 1;
  }
  std::printf("PASS: L-BFGS converged to Rosenbrock minimum on HarmonyOS\n");
  return 0;
}