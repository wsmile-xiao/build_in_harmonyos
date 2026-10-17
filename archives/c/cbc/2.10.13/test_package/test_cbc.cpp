/* cbc 2.10.13 消费者冒烟测试（test_package 内，经 CMake 链接 cbc::cbc）
 * 通过已安装公开头 <coin/Cbc_C_Interface.h> 与公开 C API 程序化建模并求解
 * 一个 0-1 背包 MILP，断言最优目标值 14 与解 (1,0,1)。
 */
#include "Cbc_C_Interface.h"
#include <cmath>
#include <cstdio>

int main() {
  const int numcols = 3, numrows = 1;
  CoinBigIndex start[4] = {0, 1, 2, 3};
  int index[3] = {0, 0, 0};
  double value[3] = {2.0, 3.0, 4.0};    /* 重量 */
  double collb[3] = {0.0, 0.0, 0.0};
  double colub[3] = {1.0, 1.0, 1.0};
  double obj[3] = {5.0, 7.0, 9.0};      /* 价值 */
  double rowlb[1] = {-1.0e30};
  double rowub[1] = {6.0};              /* 容量 6 */

  Cbc_Model *m = Cbc_newModel();
  if (!m) { std::fprintf(stderr, "Cbc_newModel failed\n"); return 2; }
  Cbc_loadProblem(m, numcols, numrows, start, index, value,
                  collb, colub, obj, rowlb, rowub);
  for (int i = 0; i < numcols; ++i) Cbc_setInteger(m, i);
  Cbc_setObjSense(m, -1.0);             /* -1 = maximize */
  Cbc_setLogLevel(m, 0);
  int rc = Cbc_solve(m);
  const double *sol = Cbc_getColSolution(m);
  double got = Cbc_getObjValue(m);
  bool ok = (rc == 0) && Cbc_isProvenOptimal(m) && sol
         && std::fabs(got - 14.0) < 1e-6
         && std::fabs(sol[0] - 1.0) < 1e-6
         && std::fabs(sol[1] - 0.0) < 1e-6
         && std::fabs(sol[2] - 1.0) < 1e-6;
  std::printf("test_cbc: obj=%.6f sol=(%.0f,%.0f,%.0f) => %s\n",
              got, sol ? sol[0] : -1, sol ? sol[1] : -1, sol ? sol[2] : -1,
              ok ? "PASS" : "FAIL");
  Cbc_deleteModel(m);
  return ok ? 0 : 1;
}