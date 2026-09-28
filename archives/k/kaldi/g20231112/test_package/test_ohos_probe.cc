// test_package/test_ohos_probe.cc
//
// 鸿蒙场景探针：kaldi 以静态库发布，消费方（如 vosk-api 的 libvosk.so）需要把
// kaldi 静态库链进共享库。本文件编译成共享库，用于验证静态库携带 -fPIC 且
// 符号在 OHOS musl 加载器下可解析（由 test_ohos_kaldi.sh dlopen 验证）。
#include "base/kaldi-common.h"
#include "matrix/kaldi-matrix.h"
#include "matrix/sp-matrix.h"
#include "fstext/fstext-lib.h"

extern "C" int kaldi_ohos_probe() {
  kaldi::Matrix<float> m(2, 2);
  m.Set(1.0f);
  kaldi::SpMatrix<float> s(2);
  s.SetDiag(2.0f);
  // 4 (矩阵元素和) + 2 + 2 (对角线) = 8
  return static_cast<int>(m.Sum() + s(0, 0) + s(1, 1));
}
