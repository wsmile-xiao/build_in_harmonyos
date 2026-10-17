/* bonmin_smoke.cpp — coinor-bonmin 1.8.9 消费者冒烟测试（R34：实质调用被测包 API）
 *
 * 只用已安装的公开头与公开库（include/coin + libbonmin.a + conan 依赖闭包）：
 * 用 Bonmin::BonminSetup + Bonmin::Bab 跑完整 B-BB（Ipopt NLP 子问题 + Cbc
 * 分支定界），求解上游 examples/CppExample 的 MINLP：
 *     min -x0-x1-x2
 *     s.t. (x1-0.5)^2 + (x2-0.5)^2 <= 0.25,  x0-x1 <= 0,  x0+x2+x3 <= 2
 *          x0 ∈ {0,1}, x3 ∈ N
 *
 * 断言：① 有可行解（bestSolution 非空）② mipStatus == FeasibleOptimal
 *       ③ bestObj 与实测最优值 -2.500141411335916 之差 < 1e-6
 * 期望值取自上游 CppExample 在本设备的实测输出
 * （`Cbc0001I Search completed - best objective -2.500141411335916`）。
 */
#include <cmath>
#include <cstdio>

#include "BonOsiTMINLPInterface.hpp"
#include "BonIpoptSolver.hpp"
#include "MyTMINLP.hpp"
#include "BonCbc.hpp"
#include "BonBonminSetup.hpp"

int main() {
  using namespace Ipopt;
  using namespace Bonmin;

  const double kExpectObj = -2.500141411335916;
  double obj = 0.0;
  int nodes = -1;
  int mip = -1;
  bool has_solution = false;
  bool optimal = false;

  SmartPtr<MyTMINLP> tminlp = new MyTMINLP;
  BonminSetup bonmin;
  bonmin.initializeOptionsAndJournalist();
  bonmin.readOptionsString("bonmin.algorithm B-BB\n");
  bonmin.initialize(GetRawPtr(tminlp));

  try {
    Bab bb;
    bb(bonmin);
    has_solution = (bb.bestSolution() != NULL);
    obj = bb.bestObj();
    nodes = bb.numNodes();
    mip = static_cast<int>(bb.mipStatus());
    optimal = (bb.mipStatus() == Bab::FeasibleOptimal);
  } catch (TNLPSolver::UnsolvedError *e) {
    std::printf("bonmin_smoke: Ipopt failed to solve the NLP subproblem\n");
  } catch (OsiTMINLPInterface::SimpleError &e) {
    std::printf("bonmin_smoke: OsiTMINLPInterface error: %s::%s\n",
                e.className().c_str(), e.methodName().c_str());
  } catch (CoinError &e) {
    std::printf("bonmin_smoke: CoinError: %s::%s %s\n", e.className().c_str(),
                e.methodName().c_str(), e.message().c_str());
  }

  const double obj_err = std::fabs(obj - kExpectObj);
  const bool ok = has_solution && optimal && (obj_err < 1e-6);
  std::printf("bonmin_smoke: obj=%.12f expect=%.12f err=%.3e nodes=%d mip=%d "
              "solution=%s optimal=%s => %s\n",
              obj, kExpectObj, obj_err, nodes, mip,
              has_solution ? "yes" : "no", optimal ? "yes" : "no",
              ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
