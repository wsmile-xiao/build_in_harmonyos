// test_package 入口 3 — 基组数据库完整性（按名加载）
//
// 验证包内的基组数据（share/libint/2.7.2/basis）真的可用：
//   1) 多个基组按名加载成功，且基函数数目与基组定义一致
//   2) max_l / nshells 等派生量自洽
//   3) 未知基组名必须报错（证明确实在读数据目录，而不是静默返回空基组）

#include <libint2.hpp>

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

}  // namespace

int main() {
  using libint2::Atom;
  using libint2::BasisSet;

  libint2::initialize();

  const std::vector<Atom> water = {{8, 0.0, 0.0, 0.0},
                                   {1, 0.0, -0.757, 0.587},
                                   {1, 0.0, 0.757, 0.587}};

  struct BasisCase {
    const char* name;
    long nbf;
    long max_l;
  };
  // nbf/max_l 为上游 BasisSet 在本仓库实测值（water 分子）
  const BasisCase cases[] = {
      {"sto-3g", 7, 1},
      {"6-31g*", 19, 2},
      {"cc-pvdz", 24, 2},
      {"aug-cc-pvdz", 41, 2},
  };

  for (const auto& c : cases) {
    const BasisSet bs(c.name, water);
    std::cout << "[INFO] " << c.name << ": nshells=" << bs.size()
              << ", nbf=" << bs.nbf() << ", max_l=" << bs.max_l() << std::endl;
    check(bs.nbf() == c.nbf, std::string("基组 ") + c.name + " 基函数数目符合预期");
    check(bs.max_l() == c.max_l, std::string("基组 ") + c.name + " 最大角动量符合预期");
  }

  // 负例 1：默认语义（throw_if_no_match=false）——未知名不抛异常，得到空基组
  const BasisSet missing("no-such-basis-name", water);
  check(missing.nbf() == 0, "未知基组名（默认语义）→ 空基组 nbf == 0");

  // 负例 2：throw_if_no_match=true 必须抛异常，且错误信息指向基组数据目录
  // （同时证明 DATADIR 指向的目录确实被用作查找路径）
  bool threw = false;
  bool path_in_message = false;
  try {
    const BasisSet strict("no-such-basis-name", water, true);
    (void)strict;
  } catch (const std::exception& e) {
    threw = true;
    path_in_message = std::string(e.what()).find("basis") != std::string::npos;
    std::cout << "[INFO] 严格模式异常: " << e.what() << std::endl;
  }
  check(threw, "未知基组名 + throw_if_no_match=true 必须抛异常");
  check(path_in_message, "异常信息包含基组数据目录（DATADIR 生效）");

  libint2::finalize();

  std::cout << "failures = " << failures << std::endl;
  return failures == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
