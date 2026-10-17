/*
 * gemmlowp OHOS-specific test — validates the library on HarmonyOS PC (OHOS/musl).
 *
 * Distinct from the upstream test/ suite (5 ctest cases). This test exercises
 * the public quantized GEMM API (gemmlowp::GemmWithOutputPipeline with
 * MakeStandardOutputPipeline) on multiple shapes/orderings and asserts real
 * observable results:
 *   1. 2x2 RowMajor x ColMajor uint8 GEMM equals hand-computed dot products.
 *   2. 3x2 x 2x4 GEMM validates accumulation over depth=2 across orders.
 *   3. Trivial 1x1 GEMM (single multiply) sanity check.
 *   4. Uses the installed static eight_bit_int_gemm library link target.
 *
 * Compile (OHOS cross toolchain, consumer point of view):
 *   clang++ --target=aarch64-linux-ohos --sysroot=<ohos native sysroot>
 *       -I<install include>/gemmlowp ohos_specific_test.cc
 *       -L<install lib> -leight_bit_int_gemm -o ohos_specific_test
 * Run on the OHOS device (arm64).
 */
#include <cstdint>
#include <cstdio>
#include <iostream>

#include "public/bit_depth.h"
#include "public/gemmlowp.h"
#include "public/map.h"
#include "public/output_stages.h"

static int failures = 0;
#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (cond) {                                                     \
            printf("  [PASS] %s\n", msg);                               \
        } else {                                                        \
            printf("  [FAIL] %s\n", msg);                               \
            failures++;                                                 \
        }                                                               \
    } while (0)

// Run a uint8 GEMM with identity quantization pipeline and check every cell.
static void RunGemmAndCheck(const std::uint8_t* lhs_data, int lhs_rows,
                            int lhs_cols, gemmlowp::MapOrder lhs_order,
                            const std::uint8_t* rhs_data, int rhs_cols,
                            gemmlowp::MapOrder rhs_order,
                            const std::int32_t* expected, const char* msg) {
  using RowMap = gemmlowp::MatrixMap<const std::uint8_t, gemmlowp::MapOrder::RowMajor>;
  using ColMap = gemmlowp::MatrixMap<const std::uint8_t, gemmlowp::MapOrder::ColMajor>;

  RowMap lhs_row(lhs_data, lhs_rows, lhs_cols);
  ColMap lhs_col(lhs_data, lhs_rows, lhs_cols);
  RowMap rhs_row(rhs_data, lhs_cols, rhs_cols);
  ColMap rhs_col(rhs_data, lhs_cols, rhs_cols);

  std::vector<std::uint8_t> out_data(lhs_rows * rhs_cols, 0);

  gemmlowp::MapOrder lhs_ord = lhs_order;
  gemmlowp::MapOrder rhs_ord = rhs_order;
  // MapOrder 不同会导致 MatrixMap 类型不同；此处按序构造对应的映射并调用。
  gemmlowp::GemmContext context;
  const auto pipeline = gemmlowp::MakeStandardOutputPipeline(0, 1, 0);
  if (lhs_ord == gemmlowp::MapOrder::RowMajor &&
      rhs_ord == gemmlowp::MapOrder::RowMajor) {
    gemmlowp::MatrixMap<std::uint8_t, gemmlowp::MapOrder::RowMajor> result(
        out_data.data(), lhs_rows, rhs_cols);
    gemmlowp::GemmWithOutputPipeline<
        std::uint8_t, std::uint8_t,
        gemmlowp::DefaultL8R8BitDepthParams>(&context, lhs_row, rhs_row,
                                             &result, 0, 0, pipeline);
  } else if (lhs_ord == gemmlowp::MapOrder::RowMajor &&
             rhs_ord == gemmlowp::MapOrder::ColMajor) {
    gemmlowp::MatrixMap<std::uint8_t, gemmlowp::MapOrder::RowMajor> result(
        out_data.data(), lhs_rows, rhs_cols);
    gemmlowp::GemmWithOutputPipeline<
        std::uint8_t, std::uint8_t,
        gemmlowp::DefaultL8R8BitDepthParams>(&context, lhs_row, rhs_col,
                                             &result, 0, 0, pipeline);
  } else if (lhs_ord == gemmlowp::MapOrder::ColMajor &&
             rhs_ord == gemmlowp::MapOrder::RowMajor) {
    gemmlowp::MatrixMap<std::uint8_t, gemmlowp::MapOrder::RowMajor> result(
        out_data.data(), lhs_rows, rhs_cols);
    gemmlowp::GemmWithOutputPipeline<
        std::uint8_t, std::uint8_t,
        gemmlowp::DefaultL8R8BitDepthParams>(&context, lhs_col, rhs_row,
                                             &result, 0, 0, pipeline);
  } else {
    gemmlowp::MatrixMap<std::uint8_t, gemmlowp::MapOrder::RowMajor> result(
        out_data.data(), lhs_rows, rhs_cols);
    gemmlowp::GemmWithOutputPipeline<
        std::uint8_t, std::uint8_t,
        gemmlowp::DefaultL8R8BitDepthParams>(&context, lhs_col, rhs_col,
                                             &result, 0, 0, pipeline);
  }

  bool ok = true;
  for (int i = 0; i < lhs_rows * rhs_cols; ++i) {
    if (static_cast<std::int32_t>(out_data[i]) != expected[i]) {
      printf("  mismatch[%d]=%d expected=%d\n", i,
             static_cast<int>(out_data[i]), expected[i]);
      ok = false;
    }
  }
  CHECK(ok, msg);
}

int main() {
  // Case 1: 2x2 RowMajor lhs * ColMajor rhs (inner product depth=2).
  {
    const std::uint8_t lhs[4] = {1, 2, 3, 4};               // [[1,2],[3,4]]
    const std::uint8_t rhs[4] = {5, 6, 7, 8};               // [[5,7],[6,8]]
    // out = lhs * rhs = [[17,23],[39,53]]
    const std::int32_t expected[4] = {17, 23, 39, 53};
    RunGemmAndCheck(lhs, 2, 2, gemmlowp::MapOrder::RowMajor,
                    rhs, 2, gemmlowp::MapOrder::ColMajor, expected,
                    "2x2 RowMajor*ColMajor GEMM equals hand-computed");
  }

  // Case 2: 2x2 RowMajor lhs * RowMajor rhs (depth=2, both row-major).
  {
    const std::uint8_t lhs[4] = {1, 2, 3, 4};               // [[1,2],[3,4]]
    const std::uint8_t rhs[4] = {5, 6, 7, 8};               // [[5,6],[7,8]]
    // out = [[1*5+2*7, 1*6+2*8],[3*5+4*7, 3*6+4*8]] = [[19,22],[43,50]]
    const std::int32_t expected[4] = {19, 22, 43, 50};
    RunGemmAndCheck(lhs, 2, 2, gemmlowp::MapOrder::RowMajor,
                    rhs, 2, gemmlowp::MapOrder::RowMajor, expected,
                    "2x2 RowMajor*RowMajor GEMM equals hand-computed");
  }

  // Case 3: 3x2 x 2x4 GEMM (depth=2, accumulation over two terms).
  {
    const std::uint8_t lhs[6] = {1, 2, 3, 4, 5, 6};   // [[1,2],[3,4],[5,6]]
    const std::uint8_t rhs[8] = {1, 0, 2, 1,
                                 0, 1, 1, 2};        // RowMajor [[1,0,2,1],[0,1,1,2]]
    // out[i][j] = lhs[i][0]*rhs[0][j] + lhs[i][1]*rhs[1][j]
    // row0: [1,2,4,5]; row1: [3,4,10,11]; row2: [5,6,16,17]
    const std::int32_t expected[12] = {1, 2, 4, 5, 3, 4, 10, 11, 5, 6, 16, 17};
    RunGemmAndCheck(lhs, 3, 2, gemmlowp::MapOrder::RowMajor,
                    rhs, 4, gemmlowp::MapOrder::RowMajor, expected,
                    "3x2 x 2x4 GEMM accumulation over depth=2");
  }

  // Case 4: 1x1 trivial GEMM.
  {
    const std::uint8_t lhs[1] = {7};
    const std::uint8_t rhs[1] = {6};
    const std::int32_t expected[1] = {42};
    RunGemmAndCheck(lhs, 1, 1, gemmlowp::MapOrder::RowMajor,
                    rhs, 1, gemmlowp::MapOrder::ColMajor, expected,
                    "1x1 trivial GEMM");
  }

  if (failures == 0) {
    printf("gemmlowp OHOS-specific test: ALL PASSED\n");
    return 0;
  }
  printf("gemmlowp OHOS-specific test: %d FAILURES\n", failures);
  return 1;
}