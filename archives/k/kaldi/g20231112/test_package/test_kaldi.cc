// test_package/test_kaldi.cc
//
// 消费方视角的上游库功能测试：真实链接并调用 kaldi 的 API。
// 覆盖 BLAS（AddMatMat -> cblas_sgemm）、LAPACK 通用矩阵求逆
// （Matrix::Invert -> sgetrf_/sgetri_）与对称packed矩阵求逆
// （SpMatrix::Invert -> ssptrf_/ssptri_，即 patches/0003 修复的 CLAPACK 原型路径）。
#include <cmath>
#include <cstdio>
#include <cstdlib>

#include "base/kaldi-common.h"
#include "matrix/kaldi-matrix.h"
#include "matrix/kaldi-vector.h"
#include "matrix/sp-matrix.h"

using namespace kaldi;

#define CHECK(cond)                                                      \
  do {                                                                   \
    ++checks;                                                            \
    if (!(cond)) {                                                       \
      std::fprintf(stderr, "FAIL: %s (line %d)\n", #cond, __LINE__);     \
      std::exit(1);                                                      \
    }                                                                    \
  } while (0)

int main() {
  int checks = 0;

  // 1) BLAS: C = A * B
  Matrix<BaseFloat> A(2, 3), B(3, 2), C(2, 2);
  A(0, 0) = 1; A(0, 1) = 2; A(0, 2) = 3;
  A(1, 0) = 4; A(1, 1) = 5; A(1, 2) = 6;
  B(0, 0) = 7;  B(0, 1) = 8;
  B(1, 0) = 9;  B(1, 1) = 10;
  B(2, 0) = 11; B(2, 1) = 12;
  C.AddMatMat(1.0f, A, kNoTrans, B, kNoTrans, 0.0f);
  CHECK(std::fabs(C(0, 0) - 58.0f) < 1e-3f);
  CHECK(std::fabs(C(0, 1) - 64.0f) < 1e-3f);
  CHECK(std::fabs(C(1, 0) - 139.0f) < 1e-3f);
  CHECK(std::fabs(C(1, 1) - 154.0f) < 1e-3f);

  // 2) LAPACK: general inverse, then M * M^-1 == I
  Matrix<BaseFloat> M(2, 2);
  M(0, 0) = 4; M(0, 1) = 7;
  M(1, 0) = 2; M(1, 1) = 6;
  BaseFloat logdet = 0.0f;
  Matrix<BaseFloat> Mi(M);
  Mi.Invert(&logdet);
  Matrix<BaseFloat> P(2, 2);
  P.AddMatMat(1.0f, M, kNoTrans, Mi, kNoTrans, 0.0f);
  CHECK(std::fabs(P(0, 0) - 1.0f) < 1e-3f);
  CHECK(std::fabs(P(0, 1) - 0.0f) < 1e-3f);
  CHECK(std::fabs(P(1, 0) - 0.0f) < 1e-3f);
  CHECK(std::fabs(P(1, 1) - 1.0f) < 1e-3f);
  // det(M) = 4*6 - 7*2 = 10
  CHECK(std::fabs(std::exp(logdet) - 10.0f) < 1e-2f);

  // 3) LAPACK packed symmetric inverse (ssptrf_ / ssptri_)
  SpMatrix<BaseFloat> S(2);
  S(0, 0) = 4; S(0, 1) = 1;
  S(1, 1) = 3;
  BaseFloat sp_logdet = 0.0f;
  SpMatrix<BaseFloat> Si(S);
  Si.Invert(&sp_logdet);
  Matrix<BaseFloat> Sd(S), Sid(Si), Q(2, 2);
  Q.AddMatMat(1.0f, Sd, kNoTrans, Sid, kNoTrans, 0.0f);
  CHECK(std::fabs(Q(0, 0) - 1.0f) < 1e-3f);
  CHECK(std::fabs(Q(0, 1) - 0.0f) < 1e-3f);
  CHECK(std::fabs(Q(1, 0) - 0.0f) < 1e-3f);
  CHECK(std::fabs(Q(1, 1) - 1.0f) < 1e-3f);
  CHECK(std::fabs(std::exp(sp_logdet) - 11.0f) < 1e-2f);

  // 4) Vector / kaldi math
  Vector<BaseFloat> v(3), w(3);
  v.Set(2.0f);
  w.Set(1.0f);
  v.AddVec(3.0f, w);
  CHECK(std::fabs(v.Sum() - 15.0f) < 1e-3f);
  CHECK(std::fabs(kaldi::Exp((BaseFloat)0.0f) - 1.0f) < 1e-5f);
  CHECK(std::fabs(kaldi::Exp((BaseFloat)1.0f) - 2.7182817f) < 1e-3f);

  std::printf("kaldi-test: %d checks passed\n", checks);
  return 0;
}
