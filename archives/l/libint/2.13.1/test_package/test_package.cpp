// libint 2.13.1 消费者验证：构造两个归一化 1s Shell，计算重叠积分并断言 ≈ 1.0
// 实质调用被测包 API（R34）：libint2::Shell / libint2::Engine<Operator::overlap>
#include <libint2.hpp>
#include <cmath>
#include <cstdlib>
#include <iostream>

int main() {
  libint2::initialize();

  // 单个 s 型原始 Gaussian，指数 1.0（构造时自动嵌入归一化系数）
  libint2::Shell::Contraction contr;
  contr.l = 0;                  // s 型
  contr.pure = false;
  contr.coeff.push_back(1.0);   // 收缩系数

  libint2::Shell sh({1.0}, {contr}, {{0.0, 0.0, 0.0}});

  // libint2 2.13: Engine 为非模板类，构造参数为 (operator, max_nprim, max_l)
  libint2::Engine engine(libint2::Operator::overlap, 1, 0);

  engine.compute(sh, sh);
  const auto* result = engine.results()[0];
  if (result == nullptr) {
    std::cerr << "FAIL: engine returned null result" << std::endl;
    return 1;
  }
  // 相同 s 型归一化高斯同中心 → 重叠积分 = 1.0
  const double S = result[0];
  std::cout << "S_ss = " << S << std::endl;
  if (std::fabs(S - 1.0) > 1e-10) {
    std::cerr << "FAIL: expected S_ss ≈ 1.0, got " << S << std::endl;
    return 1;
  }

  std::cout << "PASS: libint2 overlap integral ok" << std::endl;
  return 0;
}
