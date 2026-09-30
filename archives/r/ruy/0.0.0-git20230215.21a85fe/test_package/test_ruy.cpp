/* Installed-package consumer test for ruy.
 *
 * 以"库的使用者"身份只通过 ruy 对外公开的 API（ruy/ruy.h）完成真实的矩阵
 * 乘法，并逐元素校验数值结果。程序不使用 assert()：CMake 的 Release 配置会
 * 定义 NDEBUG，把 assert 预处理成空语句，测试会退化成"必然通过"的假测试
 * （CI 的 L1e 破坏性反向验证正是针对这种情形）。这里改用自研 CHECK 宏累计
 * 失败数，最后以非零退出码上报。
 */
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <vector>

#include "ruy/ruy.h"

namespace {

int g_checks = 0;
int g_failures = 0;

void Fail(const char* what, int line) {
  ++g_failures;
  std::fprintf(stderr, "  [FAIL] %s (test_ruy.cpp:%d)\n", what, line);
}

#define CHECK_TRUE(expr)                                            \
  do {                                                              \
    ++g_checks;                                                     \
    if (!(expr)) {                                                  \
      Fail(#expr, __LINE__);                                        \
    }                                                               \
  } while (0)

#define CHECK_INT_EQ(actual, expected)                                         \
  do {                                                                         \
    ++g_checks;                                                                \
    const long long a_ = static_cast<long long>(actual);                       \
    const long long e_ = static_cast<long long>(expected);                     \
    if (a_ != e_) {                                                            \
      std::fprintf(stderr, "  [FAIL] %s line %d: got %lld, want %lld\n",       \
                   #actual, __LINE__, a_, e_);                                 \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

#define CHECK_FLOAT_EQ(actual, expected, tol)                                  \
  do {                                                                         \
    ++g_checks;                                                                \
    const double a_ = static_cast<double>(actual);                             \
    const double e_ = static_cast<double>(expected);                           \
    if (!(std::fabs(a_ - e_) <= (tol))) {                                      \
      std::fprintf(stderr, "  [FAIL] %s line %d: got %.6f, want %.6f\n",       \
                   #actual, __LINE__, a_, e_);                                 \
      ++g_failures;                                                            \
    }                                                                          \
  } while (0)

// 参考实现：CPU 三重循环，dst = lhs * rhs（float，row-major 存法）。
std::vector<float> RefMul(const std::vector<float>& lhs, int m, int k,
                          const std::vector<float>& rhs, int n) {
  std::vector<float> out(static_cast<size_t>(m) * n, 0.0f);
  for (int i = 0; i < m; ++i) {
    for (int j = 0; j < n; ++j) {
      float acc = 0.0f;
      for (int p = 0; p < k; ++p) {
        acc += lhs[static_cast<size_t>(i) * k + p] *
               rhs[static_cast<size_t>(p) * n + j];
      }
      out[static_cast<size_t>(i) * n + j] = acc;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// T1: float 2x2 —— 基础正确性（row-major LHS × col-major RHS）
// ---------------------------------------------------------------------------
void TestFloatSquare(ruy::Context* context) {
  std::printf("T1 float 2x2 (row-major x col-major)\n");
  const float lhs_data[] = {1, 2, 3, 4};  // [[1,2],[3,4]]
  const float rhs_data[] = {1, 2, 3, 4};  // col-major -> [[1,3],[2,4]]
  float dst_data[4] = {0, 0, 0, 0};

  ruy::Matrix<float> lhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kRowMajor, lhs.mutable_layout());
  lhs.set_data(lhs_data);
  ruy::Matrix<float> rhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, rhs.mutable_layout());
  rhs.set_data(rhs_data);
  ruy::Matrix<float> dst;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, dst.mutable_layout());
  dst.set_data(dst_data);

  ruy::MulParams<float, float> mul_params;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);

  // 期望：[[1*1+2*2, 1*3+2*4],[3*1+4*2, 3*3+4*4]] = [[5,11],[11,25]]
  // dst 为 col-major 存法 => {5, 11, 11, 25}
  CHECK_FLOAT_EQ(dst_data[0], 5.0f, 1e-6);
  CHECK_FLOAT_EQ(dst_data[1], 11.0f, 1e-6);
  CHECK_FLOAT_EQ(dst_data[2], 11.0f, 1e-6);
  CHECK_FLOAT_EQ(dst_data[3], 25.0f, 1e-6);
}

// ---------------------------------------------------------------------------
// T2: float 3x2 * 2x4 —— 非方阵，与 CPU 参考实现对拍
// ---------------------------------------------------------------------------
void TestFloatRectangular(ruy::Context* context) {
  std::printf("T2 float 3x2 * 2x4 (row-major x row-major, vs reference)\n");
  const int m = 3, k = 2, n = 4;
  // lhs: 3x2 row-major
  const std::vector<float> lhs_cpu = {1, 2,
                                      3, 4,
                                      5, 6};
  // rhs: 2x4 row-major（ruy 侧按 col-major 描述同一块数据）
  const std::vector<float> rhs_cpu = {1, 0, 2, -1,
                                      0, 3, 1,  2};
  const std::vector<float> expect = RefMul(lhs_cpu, m, k, rhs_cpu, n);

  // ruy 的 kColMajor 描述：data 的第 j*m + i 项是 (i, j) 元素。
  // 这里直接把 row-major 的 rhs 转成 col-major 数组交给 ruy。
  std::vector<float> rhs_colmajor(static_cast<size_t>(k) * n);
  for (int p = 0; p < k; ++p) {
    for (int j = 0; j < n; ++j) {
      rhs_colmajor[static_cast<size_t>(j) * k + p] =
          rhs_cpu[static_cast<size_t>(p) * n + j];
    }
  }
  std::vector<float> dst_data(static_cast<size_t>(m) * n, 0.0f);

  ruy::Matrix<float> lhs;
  ruy::MakeSimpleLayout(m, k, ruy::Order::kRowMajor, lhs.mutable_layout());
  lhs.set_data(lhs_cpu.data());
  ruy::Matrix<float> rhs;
  ruy::MakeSimpleLayout(k, n, ruy::Order::kColMajor, rhs.mutable_layout());
  rhs.set_data(rhs_colmajor.data());
  ruy::Matrix<float> dst;
  ruy::MakeSimpleLayout(m, n, ruy::Order::kColMajor, dst.mutable_layout());
  dst.set_data(dst_data.data());

  ruy::MulParams<float, float> mul_params;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);

  // 逐元素比较。期望值 expect 为 row-major，元素 (i,j) 在 expect[i*n + j]；
  // ruy 的 dst 是 col-major，元素 (i,j) 在 dst_data[j*m + i]。
  //
  // 这里刻意把 3x4 全部展开成 12 条独立断言（而不是循环），使"断言条数"
  // 在源码层面就是静态可数的常量 —— 门禁与 PR 正文的通过率分母因此没有歧义，
  // 失败时也能直接由行号定位到具体元素。
  CHECK_FLOAT_EQ(dst_data[0 * m + 0], expect[0 * n + 0], 1e-5);
  CHECK_FLOAT_EQ(dst_data[1 * m + 0], expect[0 * n + 1], 1e-5);
  CHECK_FLOAT_EQ(dst_data[2 * m + 0], expect[0 * n + 2], 1e-5);
  CHECK_FLOAT_EQ(dst_data[3 * m + 0], expect[0 * n + 3], 1e-5);
  CHECK_FLOAT_EQ(dst_data[0 * m + 1], expect[1 * n + 0], 1e-5);
  CHECK_FLOAT_EQ(dst_data[1 * m + 1], expect[1 * n + 1], 1e-5);
  CHECK_FLOAT_EQ(dst_data[2 * m + 1], expect[1 * n + 2], 1e-5);
  CHECK_FLOAT_EQ(dst_data[3 * m + 1], expect[1 * n + 3], 1e-5);
  CHECK_FLOAT_EQ(dst_data[0 * m + 2], expect[2 * n + 0], 1e-5);
  CHECK_FLOAT_EQ(dst_data[1 * m + 2], expect[2 * n + 1], 1e-5);
  CHECK_FLOAT_EQ(dst_data[2 * m + 2], expect[2 * n + 2], 1e-5);
  CHECK_FLOAT_EQ(dst_data[3 * m + 2], expect[2 * n + 3], 1e-5);
}

// ---------------------------------------------------------------------------
// T3: float bias + clamp —— 校验 MulParams 的逐列后处理真的生效
// ---------------------------------------------------------------------------
void TestFloatBiasClamp(ruy::Context* context) {
  std::printf("T3 float 2x2 with bias add and clamp\n");
  const float lhs_data[] = {1, 2, 3, 4};
  const float rhs_data[] = {1, 2, 3, 4};   // col-major -> [[1,3],[2,4]]
  const float bias_data[] = {100.0f, -100.0f};
  float dst_data[4] = {0, 0, 0, 0};

  ruy::Matrix<float> lhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kRowMajor, lhs.mutable_layout());
  lhs.set_data(lhs_data);
  ruy::Matrix<float> rhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, rhs.mutable_layout());
  rhs.set_data(rhs_data);
  ruy::Matrix<float> dst;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, dst.mutable_layout());
  dst.set_data(dst_data);

  ruy::MulParams<float, float> mul_params;
  mul_params.set_bias(bias_data);
  mul_params.set_clamp_min(0.0f);
  mul_params.set_clamp_max(50.0f);
  ruy::Mul(lhs, rhs, mul_params, context, &dst);

  // bias 沿哪个维度施加由 MulParams::channel_dimension() 决定，
  // 上游 ruy/mul_params.h 中该字段**默认为 ChannelDimension::kRow**，
  // 即 bias[k] 加到 dst 的第 k 行（不是列！踩坑记录见 notes.md）。
  //
  // dst 是 col-major 2x2，元素 (i,j) 存在 data[j*2 + i]：
  //   data[0]=(0,0)=5   data[1]=(1,0)=11   data[2]=(0,1)=11   data[3]=(1,1)=25
  // 第 0 行 +bias[0]=+100：(0,0)->105、(0,1)->111，clamp(0,50) 后均为 50
  // 第 1 行 +bias[1]=-100：(1,0)->-89、(1,1)->-75，clamp(0,50) 后均为 0
  CHECK_FLOAT_EQ(dst_data[0], 50.0f, 1e-6);  // (0,0) 本行 bias=+100
  CHECK_FLOAT_EQ(dst_data[1], 0.0f, 1e-6);   // (1,0) 本行 bias=-100
  CHECK_FLOAT_EQ(dst_data[2], 50.0f, 1e-6);  // (0,1) 本行 bias=+100
  CHECK_FLOAT_EQ(dst_data[3], 0.0f, 1e-6);   // (1,1) 本行 bias=-100
}

// ---------------------------------------------------------------------------
// T4: int8 -> int32 原始累加器（量化内核路径）
// ---------------------------------------------------------------------------
void TestInt8RawAccumulators(ruy::Context* context) {
  std::printf("T4 int8 2x2 -> int32 raw accumulators\n");
  const std::int8_t lhs_data[] = {1, 2, 3, 4};
  const std::int8_t rhs_data[] = {1, 2, 3, 4};  // col-major -> [[1,3],[2,4]]
  std::int32_t dst_data[4] = {0, 0, 0, 0};

  ruy::Matrix<std::int8_t> lhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kRowMajor, lhs.mutable_layout());
  lhs.set_data(lhs_data);
  ruy::Matrix<std::int8_t> rhs;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, rhs.mutable_layout());
  rhs.set_data(rhs_data);
  ruy::Matrix<std::int32_t> dst;
  ruy::MakeSimpleLayout(2, 2, ruy::Order::kColMajor, dst.mutable_layout());
  dst.set_data(dst_data);

  // Dst 为 int32 时 mul_params 不被使用（见上游 example.cc 注释）。
  ruy::MulParams<std::int32_t, std::int32_t> mul_params;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);

  // 整数点积精确可预期：col-major 存法 => {5, 11, 11, 25}
  CHECK_INT_EQ(dst_data[0], 5);
  CHECK_INT_EQ(dst_data[1], 11);
  CHECK_INT_EQ(dst_data[2], 11);
  CHECK_INT_EQ(dst_data[3], 25);
}

// ---------------------------------------------------------------------------
// T5: 1x1 边界 + 重复调用一致性
// ---------------------------------------------------------------------------
void TestDegenerateAndRepeat(ruy::Context* context) {
  std::printf("T5 1x1 degenerate case and repeatability\n");
  const float lhs_data[] = {3.0f};
  const float rhs_data[] = {4.0f};
  float dst_data[1] = {0.0f};

  ruy::Matrix<float> lhs;
  ruy::MakeSimpleLayout(1, 1, ruy::Order::kRowMajor, lhs.mutable_layout());
  lhs.set_data(lhs_data);
  ruy::Matrix<float> rhs;
  ruy::MakeSimpleLayout(1, 1, ruy::Order::kColMajor, rhs.mutable_layout());
  rhs.set_data(rhs_data);
  ruy::Matrix<float> dst;
  ruy::MakeSimpleLayout(1, 1, ruy::Order::kColMajor, dst.mutable_layout());
  dst.set_data(dst_data);

  ruy::MulParams<float, float> mul_params;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);
  CHECK_FLOAT_EQ(dst_data[0], 12.0f, 1e-6);

  // 同一 Context 复用（上游文档允许），结果必须稳定。
  // 同样展开成 3 条独立断言，保持断言总数静态可数。
  dst_data[0] = 0.0f;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);
  CHECK_FLOAT_EQ(dst_data[0], 12.0f, 1e-6);

  dst_data[0] = 0.0f;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);
  CHECK_FLOAT_EQ(dst_data[0], 12.0f, 1e-6);

  dst_data[0] = 0.0f;
  ruy::Mul(lhs, rhs, mul_params, context, &dst);
  CHECK_FLOAT_EQ(dst_data[0], 12.0f, 1e-6);
}

}  // namespace

int main() {
  std::printf("ruy consumer test — linking against the installed package\n");
  std::printf("ruy::Mul API exercised through ruy/ruy.h only\n\n");

  ruy::Context context;
  TestFloatSquare(&context);
  TestFloatRectangular(&context);
  TestFloatBiasClamp(&context);
  TestInt8RawAccumulators(&context);
  TestDegenerateAndRepeat(&context);

  std::printf("\nchecks=%d failures=%d\n", g_checks, g_failures);
  if (g_failures != 0) {
    // 双通道上报：结构化标记便于日志采集，非零退出码供 L1e/CI 判定。
    std::printf("HMBS_TEST_PACKAGE_RESULT={\"status\":\"failed\","
                "\"checks\":%d,\"failures\":%d}\n", g_checks, g_failures);
    std::fflush(stdout);
    return 1;
  }
  std::printf("HMBS_TEST_PACKAGE_RESULT={\"status\":\"passed\","
              "\"checks\":%d,\"failures\":0}\n", g_checks);
  std::printf("ALL CONSUMER CHECKS PASSED\n");
  std::fflush(stdout);
  return 0;
}
