/* cbc 2.10.13 HarmonyOS 专项测试（test_package 内）
 * 通过已安装公开 C API 建模求解 0-1 背包 MILP，验证 CbcSolver 在 OHOS
 * 运行时（aarch64, clang/libc++）下完整求解流水线可用：建模 -> Cbc_solve
 * -> proven optimal -> 目标值 14 -> 整数解 (1,0,1)。CglLandP cut generator
 * 随 Cgl 0.60.10.1 正常装载（本测试对应该依赖包原先缺头的 R01 阻塞点）。
 */
#include "Cbc_C_Interface.h"
#include <cmath>
#include <cstdio>

int main() {
  const int numcols = 3, numrows = 1;
  CoinBigIndex start[4] = {0, 1, 2, 3};
  int index[3] = {0, 0, 0};
  double value[3] = {2.0, 3.0, 4.0};
  double collb[3] = {0.0, 0.0, 0.0};
  double colub[3] = {1.0, 1.0, 1.0};
  double obj[3] = {5.0, 7.0, 9.0};
  double rowlb[1] = {-1.0e30};
  double rowub[1] = {6.0};

  Cbc_Model *m = Cbc_newModel();
  if (!m) { std::fprintf(stderr, "Cbc_newModel failed\n"); return 2; }
  Cbc_loadProblem(m, numcols, numrows, start, index, value,
                  collb, colub, obj, rowlb, rowub);
  for (int i = 0; i < numcols; ++i) Cbc_setInteger(m, i);
  Cbc_setObjSense(m, -1.0);
  Cbc_setLogLevel(m, 0);
  int rc = Cbc_solve(m);
  const double *sol = Cbc_getColSolution(m);
  double got = Cbc_getObjValue(m);
  int nodes = Cbc_getNodeCount(m);
  bool ok = (rc == 0) && Cbc_isProvenOptimal(m) && sol
         && std::fabs(got - 14.0) < 1e-6
         && std::fabs(sol[0] - 1.0) < 1e-6
         && std::fabs(sol[1] - 0.0) < 1e-6
         && std::fabs(sol[2] - 1.0) < 1e-6;
  std::printf("cbc_ohos_test: obj=%.6f sol=(%.0f,%.0f,%.0f) nodes=%d => %s\n",
              got, sol ? sol[0] : -1, sol ? sol[1] : -1, sol ? sol[2] : -1,
              nodes, ok ? "PASS" : "FAIL");
  Cbc_deleteModel(m);
  return ok ? 0 : 1;
}