// veccore 0.8.1 消费者验证用例（R34：按业务组件的正常消费方式使用公开 API）
//
// 只包含公开头 <VecCore/VecCore>，对上游在本平台真正可用的两个后端（Scalar、
// ScalarWrapper）各跑同一组 SIMD 抽象断言，并与标准库参考值对拍。取向量/标量/
// 掩码类型的方式与上游 test/test.h 一致（vecCore::Scalar<Vector_t>、
// vecCore::Mask<Vector_t>），实例化的类型集合与上游 limits.cc 的 FloatTypes
// 对齐（Float_v / Double_v × 两个后端）。
#include <VecCore/VecCore>

#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

namespace {

int g_checks = 0;
int g_failures = 0;

void check(bool ok, const char *what)
{
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::printf("FAIL %s\n", what);
  }
}

void check_near(double got, double want, double eps, const char *what)
{
  ++g_checks;
  double denom = std::fabs(want) > 1e-12 ? std::fabs(want) : 1.0;
  double rel = std::fabs((got - want) / denom);
  if (!std::isfinite(got) || rel > eps) {
    ++g_failures;
    std::printf("FAIL %s: got=%.17g want=%.17g rel=%.3e\n", what, got, want, rel);
  }
}

template <class Vector_t>
void exercise(const char *tag, double eps)
{
  using Scalar_t = vecCore::Scalar<Vector_t>;
  using Mask_t = vecCore::Mask<Vector_t>;
  char what[96];

  // VectorSize / 广播构造 / Set / Get
  const size_t n = vecCore::VectorSize<Vector_t>();
  std::snprintf(what, sizeof what, "%s: VectorSize > 0", tag);
  check(n > 0, what);

  Vector_t a(Scalar_t(3));
  Vector_t b(Scalar_t(2));
  for (size_t i = 0; i < n; ++i) {
    std::snprintf(what, sizeof what, "%s: broadcast ctor a[%u] == 3", tag, (unsigned)i);
    check(vecCore::Get(a, i) == Scalar_t(3), what);
  }
  Vector_t c;
  vecCore::Set(c, 0, Scalar_t(7));
  std::snprintf(what, sizeof what, "%s: Set/Get round-trip", tag);
  check(vecCore::Get(c, 0) == Scalar_t(7), what);

  // 运算符 + 掩码
  Vector_t sum = a + b;
  Vector_t dif = a - b;
  Vector_t prd = a * b;
  Vector_t quo = a / b;
  std::snprintf(what, sizeof what, "%s: a+b == 5", tag);
  check(vecCore::MaskFull(sum == Vector_t(Scalar_t(5))), what);
  std::snprintf(what, sizeof what, "%s: a-b == 1", tag);
  check(vecCore::MaskFull(dif == Vector_t(Scalar_t(1))), what);
  std::snprintf(what, sizeof what, "%s: a*b == 6", tag);
  check(vecCore::MaskFull(prd == Vector_t(Scalar_t(6))), what);
  std::snprintf(what, sizeof what, "%s: a/b == 1.5", tag);
  check(vecCore::MaskFull(quo == Vector_t(Scalar_t(1.5))), what);

  Mask_t greater = a > b;
  std::snprintf(what, sizeof what, "%s: MaskFull(a>b)", tag);
  check(vecCore::MaskFull(greater), what);
  Mask_t less = a < b;
  std::snprintf(what, sizeof what, "%s: MaskEmpty(a<b)", tag);
  check(vecCore::MaskEmpty(less), what);

  // MaskedAssign / Blend
  Vector_t dst(Scalar_t(0));
  vecCore::MaskedAssign(dst, greater, b);
  std::snprintf(what, sizeof what, "%s: MaskedAssign -> 2", tag);
  check(vecCore::MaskFull(dst == Vector_t(Scalar_t(2))), what);
  Vector_t blended = vecCore::Blend(greater, a, b);
  std::snprintf(what, sizeof what, "%s: Blend -> 3", tag);
  check(vecCore::MaskFull(blended == Vector_t(Scalar_t(3))), what);

  // Load / Store
  std::vector<Scalar_t> in(n), out(n, Scalar_t(0));
  for (size_t i = 0; i < n; ++i)
    in[i] = Scalar_t(i + 1);
  Vector_t loaded = vecCore::Load<Vector_t>(in.data());
  vecCore::Store(loaded, out.data());
  for (size_t i = 0; i < n; ++i) {
    std::snprintf(what, sizeof what, "%s: Load/Store[%u]", tag, (unsigned)i);
    check(out[i] == in[i], what);
  }

  // 归约
  std::snprintf(what, sizeof what, "%s: ReduceAdd(1..n)", tag);
  check_near(vecCore::ReduceAdd(loaded), (double)n * (double)(n + 1) / 2.0, eps, what);
  std::snprintf(what, sizeof what, "%s: ReduceMin", tag);
  check(vecCore::ReduceMin(loaded) == Scalar_t(1), what);
  std::snprintf(what, sizeof what, "%s: ReduceMax", tag);
  check(vecCore::ReduceMax(loaded) == Scalar_t(n), what);

  // 向量数学函数与标准库对拍
  Vector_t x(Scalar_t(2));
  std::snprintf(what, sizeof what, "%s: Sqrt(2)", tag);
  check_near(vecCore::Get(vecCore::Sqrt(x), 0), std::sqrt(2.0), eps, what);
  std::snprintf(what, sizeof what, "%s: Pow(2,10)", tag);
  check_near(vecCore::Get(vecCore::Pow(x, Vector_t(Scalar_t(10))), 0),
             std::pow(2.0, 10.0), eps, what);
  std::snprintf(what, sizeof what, "%s: Exp(1)", tag);
  check_near(vecCore::Get(vecCore::Exp(x - Vector_t(Scalar_t(1))), 0), std::exp(1.0),
             eps, what);
  std::snprintf(what, sizeof what, "%s: Abs(-3)", tag);
  check_near(vecCore::Get(vecCore::Abs(Vector_t(Scalar_t(-3))), 0), 3.0, eps, what);
  std::snprintf(what, sizeof what, "%s: Min/Max", tag);
  check(vecCore::Get(vecCore::Min(a, b), 0) == Scalar_t(2) &&
        vecCore::Get(vecCore::Max(a, b), 0) == Scalar_t(3), what);

  // NumericLimits：向量后端与标量必须给出同一组常量（与上游 limits.cc 同口径）
  std::snprintf(what, sizeof what, "%s: NumericLimits Max/Highest", tag);
  check(vecCore::Get(vecCore::NumericLimits<Vector_t>::Max(), 0) ==
            vecCore::NumericLimits<Scalar_t>::Max() &&
        vecCore::Get(vecCore::NumericLimits<Vector_t>::Highest(), 0) ==
            vecCore::NumericLimits<Scalar_t>::Highest(), what);
  std::snprintf(what, sizeof what, "%s: NumericLimits Epsilon/Lowest/Infinity", tag);
  check(vecCore::Get(vecCore::NumericLimits<Vector_t>::Epsilon(), 0) ==
            vecCore::NumericLimits<Scalar_t>::Epsilon() &&
        vecCore::Get(vecCore::NumericLimits<Vector_t>::Lowest(), 0) ==
            vecCore::NumericLimits<Scalar_t>::Lowest() &&
        vecCore::Get(vecCore::NumericLimits<Vector_t>::Infinity(), 0) ==
            vecCore::NumericLimits<Scalar_t>::Infinity(), what);
}

} // namespace

int main()
{
  // 包头内容必须确实是上游 0.8.1
  check(VECCORE_VERSION_MAJOR == 0 && VECCORE_VERSION_MINOR == 8 &&
            VECCORE_VERSION_PATCH == 1,
        "VECCORE_VERSION_{MAJOR,MINOR,PATCH} == 0.8.1");
  check(std::string(VECCORE_VERSION) == "0.8.1", "VECCORE_VERSION string");

  exercise<vecCore::backend::Scalar::Double_v>("Scalar/Double_v", 1e-12);
  exercise<vecCore::backend::Scalar::Float_v>("Scalar/Float_v", 1e-5);
  exercise<vecCore::backend::ScalarWrapper::Double_v>("ScalarWrapper/Double_v", 1e-12);
  exercise<vecCore::backend::ScalarWrapper::Float_v>("ScalarWrapper/Float_v", 1e-5);

  std::printf("veccore consumer probe: %d checks, %d failures -> %s\n", g_checks,
              g_failures, g_failures ? "FAILED" : "PASSED");
  return g_failures ? 1 : 0;
}
