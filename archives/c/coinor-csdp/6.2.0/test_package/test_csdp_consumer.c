/* test_csdp_consumer.c — coinor-csdp 6.2.0 消费者测试（库视角，R34 实跑被测产物）。
 *
 * 用**安装后的**头文件 declarations.h 与静态库 libsdp.a 走上游 C API：
 * read_prob() 载入上游测试夹具 theta1.dat-s → initsoln() → easy_sdp() 求解。
 *
 * 断言（5 项，任一失败即非 0 退出，由 test_package/conanfile.py 的 ⑥ 捕获）：
 *   ① read_prob() 返回 0；
 *   ② 问题规模 n=50、k=104（CSDP 语义：n=矩阵维度=夹具头单个 50×50 块，
 *      k=约束数=夹具头 104；实测 read_prob 解析所得）；
 *   ③ easy_sdp() 返回 0（Success: SDP solved）；
 *   ④ primal 目标值 = 2.3000000e+01（|Δ| ≤ 1e-5）；
 *   ⑤ dual   目标值 = 2.3000000e+01（|Δ| ≤ 1e-5）。
 *
 * 数值锚点 = 上游 test/theta1.correct 的最优值（不是本机自测基线）；容差取
 * 上游 test/Makefile 注释的判据 "agree to six digits or more"（23 的 6 位有效
 * 数字 ⇒ 1e-5），DIMACS 判据 < 1.0e-6 由上游 unitTest 层复核。
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "declarations.h"

#define EXPECT_OBJ 2.3000000e+01
#define OBJ_TOL 1.0e-5 /* six digits or more（test/Makefile 注释判据） */

int main(int argc, char **argv)
{
  int n = 0, k = 0, ret, failed = 0;
  struct blockmatrix C, X, Z;
  struct constraintmatrix *constraints;
  double *a, *y, pobj = 0.0, dobj = 0.0;

  if (argc != 2) {
    fprintf(stderr, "usage: %s <problem.dat-s>\n", argv[0]);
    return 2;
  }

  /* ① 载入上游 SDPA 夹具（printlevel=1，与 csdp CLI 同款调用） */
  ret = read_prob(argv[1], &n, &k, &C, &a, &constraints, 1);
  printf("consumer[1] read_prob rc=%d (want 0)\n", ret);
  if (ret != 0) {
    printf("CONSUMER FAIL 1\n");
    return 1;
  }

  /* ② 规模与夹具文件头一致：n=50（单个 50×50 块）、k=104（约束数） */
  printf("consumer[2] n=%d k=%d (want 50/104)\n", n, k);
  if (n != 50 || k != 104) {
    printf("CONSUMER FAIL 2\n");
    return 1;
  }

  /* ③ 初始解 + 求解 */
  initsoln(n, k, C, a, constraints, &X, &y, &Z);
  ret = easy_sdp(n, k, C, a, constraints, 0.0, &X, &y, &Z, &pobj, &dobj);
  printf("consumer[3] easy_sdp rc=%d (want 0)\n", ret);
  if (ret != 0) {
    printf("CONSUMER FAIL 3\n");
    return 1;
  }

  /* ④⑤ 目标值对齐上游 .correct 最优值 */
  printf("consumer[4] pobj=%.7e (want %.7e)\n", pobj, EXPECT_OBJ);
  if (fabs(pobj - EXPECT_OBJ) > OBJ_TOL) {
    printf("CONSUMER FAIL 4\n");
    failed = 1;
  }
  printf("consumer[5] dobj=%.7e (want %.7e)\n", dobj, EXPECT_OBJ);
  if (fabs(dobj - EXPECT_OBJ) > OBJ_TOL) {
    printf("CONSUMER FAIL 5\n");
    failed = 1;
  }

  free_prob(n, k, C, a, constraints, X, y, Z);
  if (failed) {
    printf("CONSUMER FAIL\n");
    return 1;
  }
  printf("CONSUMER PASS: pobj=dobj=%.7e\n", pobj);
  return 0;
}
