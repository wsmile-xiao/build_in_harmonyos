// test_package/test.cpp — 真实调用 butteraugli 库 API（R34 实质测试）
//
// 构造两张完全相同的 16x16 单色图像（RGB 三通道），调用
// ButteraugliInterface 计算感知差异得分。完全相同图像的理论 diffvalue
// 应为 0（低于 kButteraugliGood，视为无可见差异），以此验证
// 静态库 libbutteraugli.a 与头文件 butteraugli/butteraugli.h
// 在 OHOS aarch64 平台上可正常链接与运行。
#include <cstdio>
#include <vector>

#include "butteraugli/butteraugli.h"

int main() {
  const size_t kXsize = 16;
  const size_t kYsize = 16;
  const float kGray = 0.5f;  // 线性强度值（非 gamma 校正，测试用即可）

  // rgb0 / rgb1 各含 3 个通道（R/G/B），两图完全一致。
  std::vector<butteraugli::ImageF> rgb0;
  std::vector<butteraugli::ImageF> rgb1;
  for (int c = 0; c < 3; ++c) {
    rgb0.emplace_back(kXsize, kYsize, kGray);
    rgb1.emplace_back(kXsize, kYsize, kGray);
  }

  butteraugli::ImageF diffmap(kXsize, kYsize);
  double diffvalue = -1.0;
  const bool ok = butteraugli::ButteraugliInterface(
      rgb0, rgb1, /*hf_asymmetry=*/1.0f, diffmap, diffvalue);

  if (!ok) {
    std::fprintf(stderr, "FAIL: ButteraugliInterface returned false\n");
    return 1;
  }
  // 完全相同图像：diffvalue 应极小（远小于 kButteraugliGood ~1.2 阈值）
  if (diffvalue < 0.0) {
    std::fprintf(stderr, "FAIL: unexpected negative diffvalue %f\n", diffvalue);
    return 1;
  }
  // 阈值：完全相同图像感知差应接近 0；1e-6 足够宽松（浮点计算噪声）
  if (diffvalue > 1e-6) {
    std::fprintf(stderr,
                 "FAIL: identical images should be near-zero, got %f\n",
                 diffvalue);
    return 1;
  }

  std::printf("test_butteraugli: PASS (identical 16x16 diffvalue=%f)\n",
              diffvalue);
  return 0;
}