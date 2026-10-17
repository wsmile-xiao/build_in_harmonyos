// gemmlowp consumer test — validates that a downstream project can use the
// installed public headers and link against the eight_bit_int_gemm library.
//
// Calls the public quantized GEMM API (gemmlowp::GemmWithOutputPipeline with
// MakeStandardOutputPipeline) on a small 2x2 problem and checks the resulting
// 8-bit output values, exercising the library's quantization pipeline
// end-to-end from a pure consumer perspective (public headers only).
#include <cstdint>
#include <iostream>

#include "public/bit_depth.h"
#include "public/gemmlowp.h"
#include "public/map.h"
#include "public/output_stages.h"

int main() {
  // 2x2 quantized inputs (uint8), zero_point 0, scale 1.0
  const std::uint8_t lhs_data[4] = {1, 2, 3, 4};
  const std::uint8_t rhs_data[4] = {5, 6, 7, 8};

  gemmlowp::MatrixMap<const std::uint8_t, gemmlowp::MapOrder::RowMajor> lhs(
      lhs_data, 2, 2);
  gemmlowp::MatrixMap<const std::uint8_t, gemmlowp::MapOrder::ColMajor> rhs(
      rhs_data, 2, 2);

  std::uint8_t out_data[4] = {0, 0, 0, 0};
  gemmlowp::MatrixMap<std::uint8_t, gemmlowp::MapOrder::RowMajor> result(
      out_data, 2, 2);

  // rhs 以 ColMajor 存储：data = [5,6,7,8] → 矩阵 [[5,7],[6,8]]
  // Row 1: [1*5+2*6, 1*7+2*8] = [17, 23]
  // Row 2: [3*5+4*6, 3*7+4*8] = [39, 53]
  const std::uint8_t expected[4] = {17, 23, 39, 53};

  gemmlowp::GemmContext context;
  // offsets 0, multiplier 1, shift 0: output == plain int32 GEMM result,
  // then saturated to uint8 — the expected values above are exact.
  const auto output_pipeline =
      gemmlowp::MakeStandardOutputPipeline(0, 1, 0);

  gemmlowp::GemmWithOutputPipeline<
      std::uint8_t, std::uint8_t,
      gemmlowp::DefaultL8R8BitDepthParams>(&context, lhs, rhs, &result, 0, 0,
                                           output_pipeline);

  for (int i = 0; i < 4; ++i) {
    if (out_data[i] != expected[i]) {
      std::cerr << "FAIL: out[" << i << "]=" << static_cast<int>(out_data[i])
                << " expected=" << static_cast<int>(expected[i]) << "\n";
      return 1;
    }
  }
  std::cout << "gemmlowp consumer test OK (2x2 quantized GEMM verified)\n";
  return 0;
}
