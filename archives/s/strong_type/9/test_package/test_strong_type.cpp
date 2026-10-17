/*
 * test_package 消费者验证 — strong_type 9
 *
 * 模拟业务上层组件：仅通过库安装/导出的公开头文件
 * (include/strong_type/*.hpp) 与公开 API 使用 strong_type，
 * 验证第三方使用者在 HarmonyOS PC (aarch64) 上能否编译、链接、
 * 调用并正常运行。
 */
#include <strong_type/strong_type.hpp>

#include <cstdio>
#include <unordered_set>

using namespace strong;

using meters = type<int, struct meters_, arithmetic, ordered>;

static int failures = 0;

#define CHECK(cond, msg)                                     \
  do {                                                       \
    if (cond) {                                              \
      std::printf("PASS: %s\n", msg);                        \
    } else {                                                 \
      std::printf("FAIL: %s\n", msg);                        \
      ++failures;                                            \
    }                                                        \
  } while (0)

int main() {
  // 公开 API：算术语义（add/sub/mul/div/neg）
  meters a{10};
  meters b{3};
  CHECK((a + b).value_of() == 13, "arithmetic: 10 + 3 == 13");
  CHECK((a - b).value_of() == 7, "arithmetic: 10 - 3 == 7");
  CHECK((a * b).value_of() == 30, "arithmetic: 10 * 3 == 30");
  CHECK((a / b).value_of() == 3, "arithmetic: 10 / 3 == 3");
  CHECK((-a).value_of() == -10, "arithmetic: -10");

  // 公开 API：有序比较
  CHECK(b < a ? true : false, "ordered: 3 < 10 is true");
  CHECK(a > b ? true : false, "ordered: 10 > 3 is true");

  // 公开 API：hashable + unordered_set（真实容器运行）
  using hs = type<int, struct hs_, hashable, regular>;
  std::unordered_set<hs> s;
  s.insert(hs{1});
  s.insert(hs{2});
  s.insert(hs{1});
  CHECK(s.size() == 2, "hashable: unordered_set dedup keeps 2 entries");
  CHECK(s.count(hs{2}) == 1, "hashable: set contains 2");

  // 公开 API：自增（独立类型族）
  using cnt = type<int, struct cnt_, incrementable>;
  cnt n{5};
  ++n;
  CHECK(n.value_of() == 6, "incrementable: ++5 == 6");

  std::printf("%s (%d failure%s)\n",
              failures == 0 ? "CONSUMER TEST ALL PASSED" : "CONSUMER TEST FAILED",
              failures, failures == 1 ? "" : "s");
  return failures == 0 ? 0 : 1;
}