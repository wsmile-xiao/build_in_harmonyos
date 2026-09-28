/*
 * inhomog 0.1.9.2 消费者测试（test_package）— hw-5
 *
 * 以库使用者身份编译 + 链接 libinhomog 并调用**库内真实定义**的公开 API，全部用断言
 * 决定退出码。判据逐条对过上游源码（不是猜的）：
 *   C1..C4 都打在 libinhomog 的定义上：
 *     sigma_square_invariant_I.c:71-79  flat_length_3(k[3])       = sqrt(max(TOL_LENGTH_SQUARED, Σk²))
 *     sigma_square_invariant_I.c:50-59  flat_length_3_3params(a,b,c) = 同上，三参数形态
 *   ⇒ {3,4,0}→5、{1,2,2}→3、(0,5,12)→13 是精确值；而 {0,0,0} **不返回 0**，返回
 *     fmax 托底的 sqrt(TOL_LENGTH_SQUARED) > 0 —— 这条边界行为由源码第 76 行直接读出。
 *
 * ⚠ 更正记录（本窗第一版写错过，留下以免重犯）：原先还断言了 inhomog.h:343 声明的
 *   test_power_spectrum_flatspace()，链接期真机逐字 `ld.lld: error: undefined symbol:
 *   test_power_spectrum_flatspace` —— 该函数虽在公开头里声明，但定义在
 *   lib/test_power_spectrum_flatspace.c，而那个文件**不在 libinhomog_la_SOURCES 里**
 *   （lib/Makefile.am:3-23 共 19 个源文件，实测 grep 计数=0），它只属于上游自带的同名
 *   noinst 测试程序。⇒ 公开头声明 ≠ 库导出符号，选断言目标必须回 Makefile.am 核归属。
 *
 *   C5（CLI 真实 exec，走 argp-standalone 的 --help 路径）由 test_package/conanfile.py
 *   负责，本文件不重复。
 */
#include <math.h>
#include <stdio.h>

#ifdef HAVE_CONFIG_H
#include "config.h"
#endif
#include <inhomog.h>

static int failures = 0;

static void expect_close(const char *what, double got, double want, double tol) {
  if (!isfinite(got) || fabs(got - want) > tol) {
    printf("FAIL %s: got %.17g want %.17g (tol %g)\n", what, got, want, tol);
    failures++;
  } else {
    printf("ok   %s = %.17g\n", what, got);
  }
}

static void expect_positive(const char *what, double got) {
  if (!isfinite(got) || !(got > 0.0)) {
    printf("FAIL %s: got %.17g (expected finite > 0, per fmax floor)\n", what, got);
    failures++;
  } else {
    printf("ok   %s = %.17g (>0 下限托底)\n", what, got);
  }
}

int main(void) {
  double k340[3] = {3.0, 4.0, 0.0};
  double k122[3] = {1.0, 2.0, 2.0};
  double k000[3] = {0.0, 0.0, 0.0};

  expect_close("flat_length_3({3,4,0})", flat_length_3(k340), 5.0, 1e-12);
  expect_close("flat_length_3({1,2,2})", flat_length_3(k122), 3.0, 1e-12);
  expect_close("flat_length_3_3params(0,5,12)", flat_length_3_3params(0.0, 5.0, 12.0),
               13.0, 1e-12);
  expect_positive("flat_length_3({0,0,0}) 下限托底", flat_length_3(k000));

  if (failures) {
    printf("smoke_inhomog: %d assertion(s) failed\n", failures);
    return 1;
  }
  printf("smoke_inhomog: all 4 assertions passed\n");
  return 0;
}
