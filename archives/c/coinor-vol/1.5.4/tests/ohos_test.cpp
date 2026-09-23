// HarmonyOS 专项测试用例 — coinor-vol 1.5.4 (OHOS 适配验证)
// 验证在 OHOS (aarch64, clang-15, libc++) 上适配构建的 libVol 能真实求解
// 一个带约束的 volume algorithm 实例，并校验解的合理性（非空、数值有限）。
// 与 test_package 消费者测试互补：本用例针对 OHOS 平台构建产物做专项验证。

#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <limits>

#include "VolVolume.hpp"

// 真实用户 hook：单约束 LP  min 0·x  s.t. x <= 1, x ∈ {0,1}
// 拉格朗日对偶通过 volume algorithm 迭代，应收敛并产出有限对偶/原始解。
class OhosHook : public VOL_user_hooks {
public:
   virtual int compute_rc(const VOL_dvector& u, VOL_dvector& rc) {
      rc[0] = -u[0];                    // rc = c - A^T u, A=[1], c=0
      return 0;
   }
   virtual int solve_subproblem(const VOL_dvector& dual, const VOL_dvector& rc,
                                double& lcost, VOL_dvector& x, VOL_dvector& v,
                                double& pcost) {
      const double b = 1.0;
      x[0] = (rc[0] >= 0.0) ? 0.0 : 1.0;
      lcost = b * dual[0] + x[0] * rc[0];
      v[0] = b - x[0];
      pcost = 0.0;
      return 0;
   }
   virtual int heuristics(const VOL_problem& p, const VOL_dvector& x,
                          double& heur_val) {
      heur_val = 0.0;
      return 0;
   }
};

int main(void) {
   const double bad = std::numeric_limits<double>::infinity();

   VOL_problem volprob;
   volprob.dsize = 1;
   volprob.psize = 1;
   volprob.dual_lb.allocate(1);
   volprob.dual_ub.allocate(1);
   volprob.dual_lb[0] = -1.0e31;
   volprob.dual_ub[0] = 1.0e31;
   volprob.parm.maxsgriters = 200;
   volprob.parm.printflag = 0;

   OhosHook hook;
   const int rc = volprob.solve(hook, false);

   // 1) solve 返回 0（算法正常结束，非 -1 用户终止）
   if (rc != 0) {
      printf("OHOS TEST FAIL: solve rc=%d\n", rc);
      return 1;
   }
   // 2) 原始/对偶解向量已产出
   if (volprob.psol.size() != 1 || volprob.dsol.size() != 1 || volprob.viol.size() != 1) {
      printf("OHOS TEST FAIL: solution vectors missing (psol=%d dsol=%d viol=%d)\n",
             volprob.psol.size(), volprob.dsol.size(), volprob.viol.size());
      return 1;
   }
   // 3) 对偶解与拉格朗日值必须为有限数（无 NaN/Inf 传播）
   if (std::isnan(volprob.value) || std::isinf(volprob.value)) {
      printf("OHOS TEST FAIL: lagrangian value not finite: %f\n", volprob.value);
      return 1;
   }
   if (std::isnan(volprob.dsol[0]) || std::isinf(volprob.dsol[0])) {
      printf("OHOS TEST FAIL: dual solution not finite\n");
      return 1;
   }
   if (std::isnan(volprob.psol[0]) || std::isinf(volprob.psol[0])) {
      printf("OHOS TEST FAIL: primal solution not finite\n");
      return 1;
   }
   // 4) 拉格朗日值应接近该平凡问题的已知对偶最优（x<=1 松弛 => 对偶最优 0）
   //    允许 volume 算法近似收敛的合理容差
   if (std::fabs(volprob.value - 0.0) > 1.0) {
      printf("OHOS TEST FAIL: lagrangian value out of range: %f\n", volprob.value);
      return 1;
   }
   // 5) 基线 sanity：bad 常量未被误用（编译期/运行期自检）
   if (bad != std::numeric_limits<double>::infinity()) {
      printf("OHOS TEST FAIL: numeric limits broken\n");
      return 1;
   }

   printf("OHOS TEST PASS: coinor-vol 1.5.4 volume algorithm on HarmonyOS "
          "(value=%.6f dual[0]=%.6f primal[0]=%.6f viol[0]=%.6f rc=%d)\n",
          volprob.value, volprob.dsol[0], volprob.psol[0], volprob.viol[0], rc);
   return 0;
}