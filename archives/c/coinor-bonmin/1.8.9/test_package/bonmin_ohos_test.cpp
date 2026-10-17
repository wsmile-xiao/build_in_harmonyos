/* bonmin_ohos_test.cpp — coinor-bonmin 1.8.9 HarmonyOS 专项测试
 *
 * 本用例专门覆盖鸿蒙运行时与本包安装面（区别于冒烟测试的“纯消费者”视角）：
 *  ① 断言**已安装**的 BonminConfig.h 自报 BONMIN_VERSION == "1.8.9"
 *     —— 证明测试消费的是本包安装头（include/coin/BonminConfig.h，由
 *     config_bonmin.h 安装而来），而非源码树或其它副本；
 *  ② IpoptApplicationFactory() + Initialize() 必须返回 Solve_Succeeded ——
 *     证明 conanrun 注入的 LD_LIBRARY_PATH 在 OHOS 运行时（aarch64、clang/libc++）
 *     能解析 libipopt.so，且其内部 MUMPS 直接求解器初始化成功（依赖链
 *     coinor-ipopt → mumps/openblas/Fortran 运行时全部可用）；
 *  ③ 走完整 B-BB（Ipopt NLP 子问题 + Cbc 分支定界）求解与冒烟相同的 MINLP，
 *     断言 FeasibleOptimal + bestObj = -2.5001414113（1e-6）+ numNodes >= 0。
 *
 * 上游对照期望值：examples/CppExample 实测
 * `Cbc0001I Search completed - best objective -2.500141411335916`。
 */
#include <cmath>
#include <cstdio>
#include <cstring>

#include "BonminConfig.h"
#include "IpIpoptApplication.hpp"

#include "BonOsiTMINLPInterface.hpp"
#include "BonIpoptSolver.hpp"
#include "MyTMINLP.hpp"
#include "BonCbc.hpp"
#include "BonBonminSetup.hpp"

int main() {
  using namespace Ipopt;
  using namespace Bonmin;

  // ① 安装头版本自报
  const bool version_ok =
      std::strcmp(BONMIN_VERSION, "1.8.9") == 0;
  std::printf("bonmin_ohos: installed BONMIN_VERSION=%s expect=1.8.9 => %s\n",
              BONMIN_VERSION, version_ok ? "PASS" : "FAIL");
  if (!version_ok) {
    return 1;
  }

  // ② Ipopt 运行时初始化（libipopt.so 经 conanrun 解析，MUMPS 可用）
  SmartPtr<IpoptApplication> app = IpoptApplicationFactory();
  if (IsNull(app)) {
    std::printf("bonmin_ohos: IpoptApplicationFactory returned NULL\n");
    return 1;
  }
  app->Options()->SetStringValue("linear_solver", "mumps");
  app->Options()->SetIntegerValue("print_level", 0);
  const ApplicationReturnStatus init_status = app->Initialize();
  const bool ipopt_ok = (init_status == Solve_Succeeded);
  std::printf("bonmin_ohos: IpoptApplication::Initialize()=%d expect=%d => %s\n",
              static_cast<int>(init_status), static_cast<int>(Solve_Succeeded),
              ipopt_ok ? "PASS" : "FAIL");
  if (!ipopt_ok) {
    return 1;
  }

  // ③ 完整 B-BB 求解链（Bonmin + Ipopt + Cbc）
  const double kExpectObj = -2.500141411335916;
  SmartPtr<MyTMINLP> tminlp = new MyTMINLP;
  BonminSetup bonmin;
  bonmin.initializeOptionsAndJournalist();
  bonmin.readOptionsString("bonmin.algorithm B-BB\n");
  bonmin.initialize(GetRawPtr(tminlp));

  double obj = 0.0;
  int nodes = -1;
  bool has_solution = false;
  bool optimal = false;
  try {
    Bab bb;
    bb(bonmin);
    has_solution = (bb.bestSolution() != NULL);
    obj = bb.bestObj();
    nodes = bb.numNodes();
    optimal = (bb.mipStatus() == Bab::FeasibleOptimal);
  } catch (CoinError &e) {
    std::printf("bonmin_ohos: CoinError: %s::%s %s\n", e.className().c_str(),
                e.methodName().c_str(), e.message().c_str());
  }

  const bool solve_ok =
      has_solution && optimal && (std::fabs(obj - kExpectObj) < 1e-6) &&
      (nodes >= 0);
  std::printf("bonmin_ohos: B-BB obj=%.12f expect=%.12f nodes=%d solution=%s "
              "optimal=%s => %s\n",
              obj, kExpectObj, nodes, has_solution ? "yes" : "no",
              optimal ? "yes" : "no", solve_ok ? "PASS" : "FAIL");
  return solve_ok ? 0 : 1;
}
