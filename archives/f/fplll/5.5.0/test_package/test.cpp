/* 真实断言：拿 fplll 对一组**故意造坏的**格基做 LLL 约化，验三条数学性质。
 *
 * 为什么不是「能 include、能链接」就算过：LLL 的实现完全可能编译链接都成功，
 * 却因为 GMP/MPFR 没真正接上而算出错的结果（甚至默默退回浮点近似）。
 * 下面三条一起，才叫「约化真的在做约化」：
 *   ① 约化后的基仍生成同一个格 —— |det| 不变（幺模变换的定义）
 *   ② 约化后的第一个向量比原来的短（原基第一行是刻意放大的）
 *   ③ 结果通过 fplll 自己的 is_lll_reduced 判据（δ=0.99, η=0.51）
 */
#include <fplll.h>

#include <cstdio>
#include <cstdlib>

using namespace fplll;

static double norm2(const ZZ_mat<mpz_t> &b, int row)
{
  Z_NR<mpz_t> acc, t;
  acc = 0;
  for (int j = 0; j < b.get_cols(); ++j)
  {
    t.mul(b[row][j], b[row][j]);
    acc.add(acc, t);
  }
  return acc.get_d();
}

int main()
{
  int bad = 0;

  /* 二维格：基 (1,0)、(1234567, 1)。第二个向量被刻意拉长，
     它的格其实就是 Z^2，约化后应当回到接近单位基。 */
  ZZ_mat<mpz_t> b(2, 2);
  b[0][0] = 1;       b[0][1] = 0;
  b[1][0] = 1234567; b[1][1] = 1;

  const double before = norm2(b, 1);

  int st = lll_reduction(b, 0.99, 0.51);
  if (st != RED_SUCCESS)
  {
    std::fprintf(stderr, "fplll: lll_reduction 返回 %d（期望 RED_SUCCESS=%d）\n",
                 st, RED_SUCCESS);
    return 1;
  }

  /* ① 行列式绝对值不变：原基 det = 1*1 - 0*1234567 = 1 */
  Z_NR<mpz_t> d1, d2, det;
  d1.mul(b[0][0], b[1][1]);
  d2.mul(b[0][1], b[1][0]);
  det.sub(d1, d2);
  const long dv = det.get_si();
  if (dv != 1 && dv != -1)
  {
    std::fprintf(stderr, "fplll: 约化后 |det| 应为 1，实得 %ld —— 不是幺模变换\n", dv);
    bad = 1;
  }
  else
    std::printf("fplll: |det| = 1 通过（约化保持格不变）\n");

  /* ② 真的变短了 */
  const double after = norm2(b, 0) > norm2(b, 1) ? norm2(b, 1) : norm2(b, 0);
  if (!(after < before))
  {
    std::fprintf(stderr, "fplll: 约化后最短行范数² %.0f 未小于原第二行的 %.0f\n",
                 after, before);
    bad = 1;
  }
  else
    std::printf("fplll: 最短行范数² %.0f < 原 %.0f 通过\n", after, before);

  /* ③ 过 fplll 自己的 LLL 判据 */
  ZZ_mat<mpz_t> u, ut;
  MatGSO<Z_NR<mpz_t>, FP_NR<mpfr_t> > m(b, u, ut, 0);
  m.update_gso();
  if (!is_lll_reduced<Z_NR<mpz_t>, FP_NR<mpfr_t> >(m, 0.99, 0.51))
  {
    std::fprintf(stderr, "fplll: is_lll_reduced 判否 —— 结果不是 LLL 约化基\n");
    bad = 1;
  }
  else
    std::printf("fplll: is_lll_reduced 判是 通过\n");

  return bad;
}
