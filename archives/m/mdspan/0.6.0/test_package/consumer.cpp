// mdspan 0.6.0 — test_package/consumer.cpp
// 只使用**已安装的包**（find_package(mdspan) → std::mdspan），真实调用上游公开 API
// 并断言可观察结果；末尾打印 `consumer: PASS n/n assertions` 汇总行供判读。
#include <experimental/mdspan>
#include <experimental/mdarray>

#include <array>
#include <cstddef>
#include <cstdio>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace stdex = std::experimental;

static int g_checks = 0;
static int g_fails = 0;
#define CHECK(cond)                                                        \
  do {                                                                     \
    ++g_checks;                                                            \
    if (!(cond)) {                                                         \
      ++g_fails;                                                           \
      std::printf("[consumer][FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond); \
    }                                                                      \
  } while (0)

// ── 内容指纹（§二.19：测试必须指向将安装的那一份并断言版本宏/内容指纹）────
// 本库头文件无版本宏，故用 sha256 指纹 + 交付文件数双断言：
// 期望值取自任务卡 sha 锚定的上游 tarball（sha256=79f94d7f…）内的
// include/experimental/mdspan；MDSPAN_INSTALLED_* 由 test_package/conanfile.py
// 的 generate() 对**包内实际文件**计算后经 CMake 缓存变量注入。
#ifndef MDSPAN_INSTALLED_HDR_SHA256
#define MDSPAN_INSTALLED_HDR_SHA256 ""
#endif
#ifndef MDSPAN_INSTALLED_FILECOUNT
#define MDSPAN_INSTALLED_FILECOUNT 0
#endif
static const char *kUpstreamMdspanSha256 =
    "5ff8afeba59cf18c698324d679e2c115789f99bbb8c351744ccb9462cc14e0e2";

// ── 编译期断言（单列，不与运行期断言混口径）──────────────────────────────
static_assert(stdex::extents<size_t, 3, 4>::rank() == 2, "extents rank");
static_assert(stdex::extents<size_t, 3, 4>::static_extent(1) == 4, "static_extent");
static_assert(stdex::dextents<size_t, 2>::rank_dynamic() == 2, "rank_dynamic");
static_assert(stdex::dynamic_extent == std::numeric_limits<size_t>::max(),
              "dynamic_extent sentinel");
using static_mdspan_t = stdex::mdspan<int, stdex::extents<size_t, 3, 4>>;
static_assert(std::is_trivially_copyable<static_mdspan_t>::value,
              "mdspan must be trivially copyable (上游 ctest_trivially_copyable 同口径)");
static_assert(std::is_standard_layout<static_mdspan_t>::value,
              "mdspan must be standard layout (上游 ctest_standard_layout 同口径)");
static_assert(stdex::layout_right::mapping<stdex::dextents<size_t, 2>>
                  ::is_always_unique(),
              "layout_right always unique");
static_assert(stdex::layout_left::mapping<stdex::dextents<size_t, 2>>
                  ::is_always_exhaustive(),
              "layout_left always exhaustive");
static_assert(std::is_default_constructible<stdex::default_accessor<double>>::value,
              "default_accessor default constructible");
// constexpr 求值：extents 与 mdspan 的元素访问在常量表达式中可用
static_assert(stdex::extents<size_t, 2, 3>{}.extent(0) == 2, "constexpr extent");
constexpr std::array<int, 4> kConstexprBuf = {10, 20, 30, 40};
constexpr stdex::mdspan<const int, stdex::extents<size_t, 2, 2>> kConstexprMd(
    kConstexprBuf.data());
static_assert(kConstexprMd(1, 1) == 40, "constexpr mdspan element access");
static_assert(kConstexprMd.size() == 4, "constexpr mdspan size");
static constexpr int kCompileTimeAssertions = 11;

int main() {
  // 1) 交付物指纹与文件数
  CHECK(std::string(MDSPAN_INSTALLED_HDR_SHA256) == kUpstreamMdspanSha256);
  CHECK(MDSPAN_INSTALLED_FILECOUNT == 21);

  // 2) 静态 extents + layout_right（最后一个下标最快）
  std::array<double, 12> buf{};
  for (size_t i = 0; i < buf.size(); ++i) buf[i] = static_cast<double>(i);
  stdex::mdspan<double, stdex::extents<size_t, 3, 4>> m(buf.data());
  CHECK(m.rank() == 2);
  CHECK(m.rank_dynamic() == 0);
  CHECK(m.size() == 12);
  CHECK(m.extent(0) == 3);
  CHECK(m.extent(1) == 4);
  CHECK(m.data_handle() == buf.data());
  CHECK(m(0, 0) == 0.0);
  CHECK(m(1, 0) == 4.0);   // layout_right: stride(1)=1, stride(0)=4
  CHECK(m(2, 3) == 11.0);
  CHECK(m.is_unique());
  CHECK(m.is_exhaustive());
  CHECK(m.stride(0) == 4);
  CHECK(m.stride(1) == 1);
  m(2, 3) = -7.5;
  CHECK(buf[11] == -7.5);  // 视图写入落到同一块存储

  // 3) layout_left：第一个下标最快
  stdex::mdspan<double, stdex::extents<size_t, 3, 4>, stdex::layout_left>
      ml(buf.data());
  CHECK(ml(1, 0) == 1.0);  // 与 layout_right 的 4.0 相反
  CHECK(ml(2, 3) == -7.5);  // 两种 layout 索引同一块存储：上面 layout_right 写入的 -7.5
  CHECK(ml.stride(0) == 1);
  CHECK(ml.stride(1) == 3);

  // 4) 动态 extents
  std::vector<double> v(20);
  for (size_t i = 0; i < v.size(); ++i) v[i] = static_cast<double>(i * 2);
  stdex::mdspan<double, stdex::dextents<size_t, 2>> dm(v.data(), 4, 5);
  CHECK(dm.rank() == 2);
  CHECK(dm.rank_dynamic() == 2);
  CHECK(dm.extent(0) == 4);
  CHECK(dm.extent(1) == 5);
  CHECK(dm.size() == 20);
  CHECK(dm(3, 4) == 38.0);  // layout_right 下标 3*5+4 = 19 → v[19] = 19*2
  CHECK(dm(3, 4) == dm.data_handle()[19]);

  // 5) layout_stride：手工给 strides
  std::array<size_t, 2> strides{{1, 5}};  // 列间距 5 > 行长 4，制造跨行步长
  stdex::layout_stride::mapping<stdex::dextents<size_t, 2>> sm(
      stdex::dextents<size_t, 2>(3, 4), strides);
  stdex::mdspan<double, stdex::dextents<size_t, 2>, stdex::layout_stride> sdm(
      v.data(), sm);
  CHECK(sdm.stride(0) == 1);
  CHECK(sdm.stride(1) == 5);
  CHECK(sdm.extent(0) == 3);
  CHECK(sdm.extent(1) == 4);
  CHECK(sdm(1, 2) == v[11]);  // 手工 strides {1,5}：1*1 + 2*5 = 11
  CHECK(sdm(1, 1) == v[6]);  // 1*1 + 1*5 = 6

  // 6) submdspan：切出前两行
  auto sub = stdex::submdspan(m, std::pair<size_t, size_t>{0, 2},
                              stdex::full_extent);
  CHECK(sub.extent(0) == 2);
  CHECK(sub.extent(1) == 4);
  CHECK(sub.size() == 8);
  CHECK(sub(1, 0) == m(1, 0));
  CHECK(sub(1, 3) == m(1, 3));

  // 7) mdarray（P0009 owning 容器）与 mdspan 往返
  stdex::mdarray<double, stdex::dextents<size_t, 2>> a(3, 4);
  CHECK(a.size() == 12);
  CHECK(a.extent(0) == 3);
  CHECK(a.extent(1) == 4);
  CHECK(a.data() != nullptr);
  a(1, 2) = 7.5;
  CHECK(a(1, 2) == 7.5);
  CHECK(a.data()[6] == 7.5);
  stdex::mdspan<double, stdex::dextents<size_t, 2>> av = a;
  CHECK(av.data_handle() == a.data());
  CHECK(av(1, 2) == 7.5);
  av(0, 0) = -1.25;
  CHECK(a(0, 0) == -1.25);  // 视图与容器共享存储

  // 8) 零 extent 与单元素边界
  stdex::mdspan<double, stdex::dextents<size_t, 2>> empty(v.data(), 0, 5);
  CHECK(empty.size() == 0);
  std::array<int, 1> one{{42}};
  stdex::mdspan<int, stdex::dextents<size_t, 1>> one_m(one.data(), 1);
  CHECK(one_m.size() == 1);
  CHECK(one_m(0) == 42);

  std::printf("consumer: %s %d/%d assertions (compile-time static_assert=%d)\n",
              g_fails == 0 ? "PASS" : "FAIL", g_checks - g_fails, g_checks,
              kCompileTimeAssertions);
  return g_fails == 0 ? 0 : 1;
}
