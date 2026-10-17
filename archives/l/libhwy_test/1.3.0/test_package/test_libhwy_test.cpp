// Consumer test for libhwy_test 1.3.0 (Google Highway "hwy_test" test support library).
//
// 消费者视角：只用包内安装的 hwy/tests/{test_util.h,test_util-inl.h,hwy_gtest.h}
// 与 libhwy_test.a（经 hwy::hwy_test 链接）实跑本文件，逐项 Check() 断言并输出
// 机器可解析的用例计数行（供 test_package/conanfile.py 读取，禁止硬编码）。
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include "hwy/base.h"
#include "hwy/highway.h"
#include "hwy/tests/hwy_gtest.h"       // 交付的 standalone GTest 兼容运行器
#include "hwy/tests/test_util-inl.h"   // For* 向量长度枚举器 + test_util.h
#include "hwy/tests/test_util.h"

namespace hn = hwy::HWY_NAMESPACE;

namespace {

int g_checks = 0;
int g_failures = 0;
int g_vector_calls = 0;
int g_type_calls = 0;
bool g_bad_lanes = false;

void Check(bool ok, const char* what) {
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::fprintf(stderr, "FAIL: %s\n", what);
  } else {
    std::fprintf(stderr, "ok: %s\n", what);
  }
}

// test_util-inl.h 的核心能力：为每种 lane 类型枚举所有合法向量长度。
struct CountVectorCalls {
  template <class T, class D>
  void operator()(T /*t*/, D d) const {
    const size_t lanes = hn::Lanes(d);
    ++g_vector_calls;
    if (lanes == 0 || lanes > hn::MaxLanes(d)) {
      g_bad_lanes = true;
    }
  }
};

struct CountTypes {
  template <class T>
  void operator()(T /*t*/) const {
    ++g_type_calls;
  }
};

}  // namespace

int main() {
  // 1) 交付头文件自报的版本指纹（1.3.0 → HWY_MAJOR 1 / HWY_MINOR 3）
  Check(HWY_MAJOR == 1 && HWY_MINOR == 3, "installed headers report hwy 1.3");

  // 2) hwy 核心库（hwy_test 的 PUBLIC 依赖）可用
  Check(hwy::SupportedTargets() != 0, "hwy::SupportedTargets() is non-zero");

  // 3) test_util.h 的确定性随机源：同种子同序列
  hwy::RandomState rng_a(0x5EED1234u);
  hwy::RandomState rng_b(0x5EED1234u);
  bool same = true;
  uint64_t seq_a[8] = {};
  uint64_t seq_c[8] = {};
  for (int i = 0; i < 8; ++i) {
    seq_a[i] = rng_a();
    same &= (seq_a[i] == rng_b());
  }
  Check(same, "RandomState(same seed) yields identical sequences");

  // 4) 不同种子给出不同序列
  hwy::RandomState rng_c(0x0BADF00Du);
  bool differs = false;
  for (int i = 0; i < 8; ++i) {
    seq_c[i] = rng_c();
    differs |= (seq_c[i] != seq_a[i]);
  }
  Check(differs, "RandomState(different seed) diverges");

  // 5–7) test_util.h 的 TypeName 命名（u/i/f + 位宽 + x 车道数）
  const std::string n_f32x4 = hwy::TypeName(float(), 4);
  const std::string n_u64x2 = hwy::TypeName(uint64_t(), 2);
  const std::string n_i16 = hwy::TypeName(int16_t(), 1);
  Check(n_f32x4 == "f32x4", "TypeName(float,4) == f32x4");
  Check(n_u64x2 == "u64x2", "TypeName(uint64,2) == u64x2");
  Check(!n_i16.empty() && n_i16.compare(0, 3, "i16") == 0,
        "TypeName(int16,1) starts with i16");

  // 8) test_util.h 的随机有限值 + hwy 向量运算往返（test_util 与 hwy 的联合使用）
  hwy::RandomState rng_d(0xABCDEF01u);
  const float f = hwy::RandomFiniteValue<float>(&rng_d);
  Check(std::isfinite(f) && f == f, "RandomFiniteValue<float> is finite");

  // 9) 整数重载同样按种子确定（同种子两次独立序列逐项一致）
  hwy::RandomState rng_i1(0x13572468u);
  hwy::RandomState rng_i2(0x13572468u);
  bool int_same = true;
  for (int k = 0; k < 8; ++k) {
    int_same &= (hwy::RandomFiniteValue<int32_t>(&rng_i1) ==
                 hwy::RandomFiniteValue<int32_t>(&rng_i2));
  }
  Check(int_same, "RandomFiniteValue<int32> is deterministic per seed");

  const hn::ScalableTag<float> df;
  HWY_ALIGN float buf[HWY_MAX_LANES_D(hn::ScalableTag<float>)];
  const auto v = hn::Set(df, f);
  hn::Store(v, df, buf);
  Check(buf[0] == f, "Set/Store round-trip through hwy ops preserves value");

  // 9) ForAllTypes + ForPartialVectors：枚举面非空且车道数合法
  hwy::HWY_NAMESPACE::ForAllTypes(CountTypes());
  hwy::HWY_NAMESPACE::ForAllTypes(
      hwy::HWY_NAMESPACE::ForPartialVectors<CountVectorCalls>());
  Check(g_type_calls > 0, "ForAllTypes visits at least one lane type");
  Check(g_vector_calls > 0, "ForPartialVectors enumerates vector lengths");
  Check(!g_bad_lanes, "[1, MaxLanes] holds for every enumerated vector");

  // 10–11) 交付的 hwy_gtest.h standalone 运行器：--gtest_filter 解析与匹配
  const char* argv[] = {"test_libhwy_test", "--gtest_filter=DeliveredSuite.*"};
  hwy::InitTestProgramOptions(2, argv);
  Check(hwy::TestNameMatchesGTestFilter("DeliveredSuite.Case"),
        "hwy_gtest filter accepts matching test name");
  Check(!hwy::TestNameMatchesGTestFilter("OtherSuite.Case"),
        "hwy_gtest filter rejects non-matching test name");

  std::printf("LIBSHWY_TEST_CONSUMER checks_total=%d checks_passed=%d checks_failed=%d "
              "vector_calls=%d type_calls=%d typename=%s\n",
              g_checks, g_checks - g_failures, g_failures, g_vector_calls,
              g_type_calls, n_f32x4.c_str());
  return g_failures == 0 ? 0 : 1;
}
