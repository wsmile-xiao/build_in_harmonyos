// mdspan 0.6.0 — test_package/ohos_special_test.cpp
// 鸿蒙平台专项测试（PR 正文「鸿蒙特有测试」行的来源之一）。
// `#ifdef __OHOS__` 分支带实质校验（字节序 / 指针宽度 / libc++ 能力 /
// 堆与栈上的视图读写 / ABI 尺寸 / 两种 layout 同存储别名），
// 不是空壳 stub；非 OHOS 分支只打提示并返回 0（本包只面向 OHOS aarch64）。
#include <experimental/mdspan>

#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <type_traits>
#include <vector>

namespace stdex = std::experimental;

static int g_checks = 0;
static int g_fails = 0;
#define CHECK(cond)                                                        \
  do {                                                                     \
    ++g_checks;                                                            \
    if (!(cond)) {                                                         \
      ++g_fails;                                                           \
      std::printf("[ohos][FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond);  \
    }                                                                      \
  } while (0)

using static_mdspan_t = stdex::mdspan<int, stdex::extents<size_t, 4, 4>>;
using dyn_mdspan_t = stdex::mdspan<double, stdex::dextents<size_t, 2>>;

// 设备 clang 在常量表达式里对 mdspan 元素求值（平台无关但由本编译器背书）
constexpr int kConstexprProbe[] = {1, 2, 3, 4};
constexpr stdex::mdspan<const int, stdex::extents<size_t, 2, 2>> kConstexprView(
    kConstexprProbe);
static_assert(kConstexprProbe[0] == 1 && kConstexprView(0, 1) == 2,
              "device clang must constant-evaluate mdspan element access");

#ifdef __OHOS__

static int platform_checks() {
  // 1) 工具链宏：OHOS 目标三件套
  CHECK(__OHOS__ == 1);
  CHECK(__OHOS_FAMILY__ == 1);
  CHECK(sizeof(__OHOS_Major__) > 0);  // 宏存在且参与编译

  // 2) 字节序（OHOS aarch64 必须小端）与指针宽度
  const std::uint32_t probe = 0x01020304u;
  const unsigned char *p = reinterpret_cast<const unsigned char *>(&probe);
  CHECK(p[0] == 0x04u && p[3] == 0x01u);
  CHECK(sizeof(void *) == 8);
  CHECK(sizeof(size_t) == 8);

  // 3) 标准库能力：OHOS SDK 使用 libc++
#ifdef _LIBCPP_VERSION
  CHECK(_LIBCPP_VERSION > 0);
#else
  CHECK(false && "expected libc++ on the OHOS SDK");
#endif

  // 4) ABI：mdspan 是「指针 + mapping + accessor」的平凡类型
  CHECK(std::is_trivially_copyable<static_mdspan_t>::value);
  CHECK(std::is_standard_layout<static_mdspan_t>::value);
  CHECK(sizeof(static_mdspan_t) <= 16);

  // 5) 平坦 memcpy 后视图等价（平凡拷贝的真实用途）
  int storage[16];
  for (int i = 0; i < 16; ++i) storage[i] = i * 3;
  static_mdspan_t src(storage);
  static_mdspan_t dst(storage);
  std::memcpy(&dst, &src, sizeof(src));
  CHECK(dst.data_handle() == src.data_handle());
  CHECK(dst(3, 3) == 45 && src(3, 3) == 45);  // storage[15] = 15*3

  // 6) 堆上百万级元素的视图读写（OHOS 堆 + std::vector 分配路径）
  const size_t rows = 1024, cols = 1024;  // 8 MiB
  std::vector<double> big(rows * cols, 1.0);
  CHECK(reinterpret_cast<std::uintptr_t>(big.data()) % alignof(double) == 0);
  dyn_mdspan_t big_view(big.data(), rows, cols);
  CHECK(big_view.size() == rows * cols);
  CHECK(big_view.extent(0) == rows && big_view.extent(1) == cols);
  big_view(0, 0) = 2.0;
  big_view(rows - 1, cols - 1) = 3.0;
  CHECK(big[0] == 2.0);
  CHECK(big[rows * cols - 1] == 3.0);
  // 逐行写入递增值，再按视图下标回读，验证跨页/跨缓存行寻址
  for (size_t i = 0; i < rows; ++i) big_view(i, i % cols) = static_cast<double>(i);
  bool roundtrip = true;
  for (size_t i = 0; i < rows; ++i)
    if (big[i * cols + (i % cols)] != static_cast<double>(i)) roundtrip = false;
  CHECK(roundtrip);

  // 7) 栈上固定缓冲的视图（OHOS 线程栈受限场景）
  int stack_buf[64];
  for (int i = 0; i < 64; ++i) stack_buf[i] = -i;
  stdex::mdspan<int, stdex::dextents<size_t, 1>> stack_view(stack_buf, 64);
  CHECK(stack_view.size() == 64);
  CHECK(stack_view(0) == 0 && stack_view(63) == -63);
  stack_view(10) = 100;
  CHECK(stack_buf[10] == 100);

  // 8) layout_left / layout_right 对同一块存储的别名关系
  int grid[16];
  for (int i = 0; i < 16; ++i) grid[i] = i;
  stdex::mdspan<int, stdex::extents<size_t, 4, 4>, stdex::layout_right> r(grid);
  stdex::mdspan<int, stdex::extents<size_t, 4, 4>, stdex::layout_left> l(grid);
  CHECK(r(1, 0) == 4 && l(1, 0) == 1);
  CHECK(r(3, 3) == 15 && l(3, 3) == 15);  // 最后一个元素两种 layout 同址

  // 9) 跨语言宏一致性：C++20 特性在 OHOS libc++ 上的可用性不作假设
  CHECK(sizeof(kConstexprView) == sizeof(const int *));

  return g_fails;
}

int main() {
  int fails = platform_checks();
  if (fails == 0) {
    std::printf("mdspan 0.6.0 OHOS special test: ALL OK (%d checks)\n", g_checks);
    return 0;
  }
  std::printf("mdspan 0.6.0 OHOS special test: %d/%d FAILED\n", fails, g_checks);
  return 1;
}

#else  // !__OHOS__

int main() {
  std::printf("note: compiled without __OHOS__ (unexpected on this host); "
              "%d static assertions still enforced at compile time\n",
              1);
  return 0;
}

#endif
