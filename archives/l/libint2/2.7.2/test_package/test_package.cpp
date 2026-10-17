// test_package — libint2 消费者测试
//
// 通过公开 C++ API（libint2.hpp）实际计算 H2O / STO-3G 的
//   1) 1 电子重叠积分矩阵 S
//   2) 2 电子库仑积分 (ij|kl)
// 并校验：基组加载、基函数计数、S 对角元归一化、S 对称性、
// 双电子积分的置换对称性、同中心 s×p 宇称零元与 Schwarz 不等式。
//
// 这是真实 API 调用测试（R34），任何一项失败都以非 0 退出码结束。

#include <libint2.hpp>

#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
  std::cout << (ok ? "[PASS] " : "[FAIL] ") << what << std::endl;
  if (!ok) ++failures;
}

void report(const std::string& what, double value) {
  std::cout << "[INFO] " << what << " = " << value << std::endl;
}

}  // namespace

int main() {
  using libint2::Atom;
  using libint2::BasisSet;
  using libint2::Engine;
  using libint2::Operator;

  libint2::initialize();

  // ---- 基组加载（走 DATADIR 数据目录，验证包内基组数据可用）----
  const std::vector<Atom> atoms = {{8, 0.0, 0.0, 0.0},
                                   {1, 0.0, -0.757, 0.587},
                                   {1, 0.0, 0.757, 0.587}};  // H2O
  const BasisSet obs("sto-3g", atoms);
  const std::size_t nbf = static_cast<std::size_t>(obs.nbf());
  std::cout << "[INFO] BasisSet(sto-3g): nshells=" << obs.size() << ", nbf=" << nbf
            << ", max_l=" << obs.max_l() << std::endl;
  check(nbf == 7, "H2O/STO-3G 基函数数目 == 7");

  // 上游 STO-3G 壳层顺序：0=O 1s, 1=O 2s, 2=O 2p, 3=H 1s, 4=H 1s
  std::vector<std::size_t> offset(obs.size());
  for (std::size_t i = 0, off = 0; i != obs.size(); ++i) {
    offset[i] = off;
    off += obs[i].size();
  }

  // ---- 1 电子重叠积分 ----
  Engine s_engine(Operator::overlap, obs.max_nprim(),
                  static_cast<int>(obs.max_l()));
  std::vector<double> S(nbf * nbf, 0.0);
  for (std::size_t i = 0; i != obs.size(); ++i) {
    for (std::size_t j = 0; j != obs.size(); ++j) {
      s_engine.compute(obs[i], obs[j]);
      const auto* buf = s_engine.results()[0];
      if (buf == nullptr) continue;  // 该壳层对在此算符下无贡献
      for (std::size_t a = 0; a != obs[i].size(); ++a)
        for (std::size_t b = 0; b != obs[j].size(); ++b)
          S[(offset[i] + a) * nbf + offset[j] + b] = buf[a * obs[j].size() + b];
    }
  }

  bool diagonal_is_unit = true;
  double max_asymmetry = 0.0;
  double trace = 0.0;
  for (std::size_t i = 0; i != nbf; ++i) {
    trace += S[i * nbf + i];
    if (std::fabs(S[i * nbf + i] - 1.0) > 1e-12) diagonal_is_unit = false;
    for (std::size_t j = 0; j != nbf; ++j)
      max_asymmetry =
          std::max(max_asymmetry, std::fabs(S[i * nbf + j] - S[j * nbf + i]));
  }
  report("trace(S)", trace);
  report("max|S(i,j)-S(j,i)|", max_asymmetry);
  check(diagonal_is_unit, "重叠矩阵对角元 == 1（归一化基函数）");
  check(max_asymmetry < 1e-12, "重叠矩阵对称 (S(i,j) == S(j,i))");

  // ---- 2 电子库仑积分 (ij|kl) ----
  // 取壳层块的第一个分量做定性校验（(s,s) 壳层块即该积分本身）
  Engine eri_engine(Operator::coulomb, obs.max_nprim(),
                    static_cast<int>(obs.max_l()));
  auto eri = [&](std::size_t i, std::size_t j, std::size_t k, std::size_t l) {
    eri_engine.compute(obs[i], obs[j], obs[k], obs[l]);
    const auto* buf = eri_engine.results()[0];
    return buf == nullptr ? 0.0 : buf[0];
  };

  const double e_0000 = eri(0, 0, 0, 0);
  const double e_0011 = eri(0, 0, 1, 1);
  const double e_0101 = eri(0, 1, 0, 1);
  const double e_1111 = eri(1, 1, 1, 1);
  report("(00|00)", e_0000);
  report("(00|11)", e_0011);
  report("(01|01)", e_0101);
  report("(11|11)", e_1111);
  check(e_0000 > 0.0, "库仑积分 (00|00) > 0");

  // 置换对称性（取非零元，避免用平凡零元自证）
  report("(11|00)", eri(1, 1, 0, 0));
  check(std::fabs(e_0011 - eri(1, 1, 0, 0)) < 1e-12, "置换对称 (ij|kl) == (kl|ij)");
  report("(10|01)", eri(1, 0, 0, 1));
  check(std::fabs(e_0101 - eri(1, 0, 0, 1)) < 1e-12, "置换对称 (ij|kl) == (ji|kl)");
  report("(01|10)", eri(0, 1, 1, 0));
  check(std::fabs(e_0101 - eri(0, 1, 1, 0)) < 1e-12, "置换对称 (ij|kl) == (ij|lk)");

  // 同中心 s×p 乘积的宇称： (ss|s p_x) 等整型必然为 0
  const double e_0002 = eri(0, 0, 0, 2);
  const double e_0012 = eri(0, 0, 1, 2);
  const double e_0123 = eri(0, 1, 2, 3);
  report("(00|02)", e_0002);
  report("(00|12)", e_0012);
  report("(01|23)", e_0123);
  check(std::fabs(e_0002) < 1e-14 && std::fabs(e_0012) < 1e-14 &&
            std::fabs(e_0123) < 1e-14,
        "同中心 s×p 宇称零元 (ss|s p) == 0");

  // Schwarz 不等式（取非零元）
  const double schwarz_lhs = std::fabs(e_0011);
  const double schwarz_rhs = std::sqrt(std::fabs(e_0000 * e_1111));
  report("|(00|11)|", schwarz_lhs);
  report("sqrt((00|00)*(11|11))", schwarz_rhs);
  check(schwarz_lhs <= schwarz_rhs + 1e-12,
        "Schwarz 不等式 |(ij|kl)| <= sqrt((ij|ij)(kl|kl))");

  libint2::finalize();

  std::cout << "failures = " << failures << std::endl;
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
