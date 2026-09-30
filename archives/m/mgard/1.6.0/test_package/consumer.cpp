// mgard 1.6.0 消费者测试 — 真实调用公开 API（R34）
// compress/decompress roundtrip：误差可控断言（max err <= tolerance）
// 与有损压缩有效断言（压缩字节小于原始字节，平滑函数 + 宽松容差）。
#include <cmath>
#include <cstddef>
#include <iostream>
#include <vector>

#include "mgard/compress.hpp"

int main() {
  // 1D 平滑函数：f(x) = 5*sin(3x) - 2*cos(7x)（上游 example 同款）
  const std::size_t N = 1024;
  std::vector<float> v(N);
  for (std::size_t i = 0; i < N; ++i) {
    const float x = static_cast<float>(i) / static_cast<float>(N);
    v[i] = 5 * std::sin(3 * x) - 2 * std::cos(7 * x);
  }

  // 统一网格 [0,1]（省略坐标数组）
  const mgard::TensorMeshHierarchy<1, float> hierarchy({N});
  const float s = 0.0;      // L2 平滑度
  const float tolerance = 0.5;

  const mgard::CompressedDataset<1, float> compressed =
      mgard::compress(hierarchy, v.data(), s, tolerance);
  const mgard::DecompressedDataset<1, float> decompressed =
      mgard::decompress(compressed);
  const float *const out =
      reinterpret_cast<const float *>(decompressed.data());

  // 断言 1：逐点误差不超过容差（MGARD 误差可控保证）
  float max_err = 0.0;
  for (std::size_t i = 0; i < N; ++i) {
    const float err = std::fabs(v[i] - out[i]);
    if (err > max_err) {
      max_err = err;
    }
  }
  std::cout << "compressed bytes : " << compressed.size() << "\n"
            << "raw bytes        : " << v.size() * sizeof(float) << "\n"
            << "max abs error    : " << max_err << "\n";
  if (max_err > tolerance) {
    std::cerr << "FAIL: max error " << max_err
              << " exceeds tolerance " << tolerance << "\n";
    return 1;
  }

  // 断言 2：对平滑函数 + 该容差，有损压缩应减小数据量
  if (compressed.size() >= v.size() * sizeof(float)) {
    std::cerr << "FAIL: compression did not reduce size\n";
    return 1;
  }

  std::cout << "PASS: mgard compress/decompress roundtrip ("
            << compressed.size() << " bytes)\n";
  return 0;
}
