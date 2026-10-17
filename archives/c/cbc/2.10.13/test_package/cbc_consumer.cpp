/* cbc 2.10.13 消费者用例（test_package 内）
 * 模拟业务上层组件/应用：仅通过 cbc 已安装/导出的公开头文件
 * （<coin/Cbc_C_Interface.h>）、公开 API、正常链接目标（cbc::cbc 及其
 * 传递依赖）与运行时产物使用该库，验证第三方使用者编译、链接、调用并
 * 正常运行。使用 Cbc_loadProblem 建模一个生产混合 MILP（自包含，无外部
 * 数据依赖），求解并断言最优目标值。
 * 模型：max 30x1 + 20x2，s.t. 2x1 + x2 <= 8, x1 + 3x2 <= 9，x 整数 >= 0。
 * 枚举最优点：x1=3,x2=2 -> 3*30+2*20=130（2*3+2=8<=8, 3+6=9<=9，恰在边界）。
 */
#include "Cbc_C_Interface.h"
#include <cmath>
#include <cstdio>

int main() {
  const int numcols = 2, numrows = 2;
  CoinBigIndex start[3] = {0, 2, 4};
  int index[4] = {0, 1, 0, 1};
  double value[4] = {2.0, 1.0, 1.0, 3.0};
  double collb[2] = {0.0, 0.0};
  double colub[2] = {1.0e30, 1.0e30};
  double obj[2] = {30.0, 20.0};
  double rowlb[2] = {-1.0e30, -1.0e30};
  double rowub[2] = {8.0, 9.0};

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
  bool ok = (rc == 0) && Cbc_isProvenOptimal(m) && sol
         && std::fabs(got - 130.0) < 1e-6
         && std::fabs(sol[0] - 3.0) < 1e-6
         && std::fabs(sol[1] - 2.0) < 1e-6;
  std::printf("cbc_consumer: obj=%.6f sol=(%.0f,%.0f) => %s\n",
              got, sol ? sol[0] : -1, sol ? sol[1] : -1,
              ok ? "PASS" : "FAIL");
  Cbc_deleteModel(m);
  return ok ? 0 : 1;
}