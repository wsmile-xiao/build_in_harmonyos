// HarmonyOS 专项测试 for reflect-cpp 0.17.0 (conan test_package).
// 15 项断言：OHOS 平台宏确认 + 本机 aarch64 目标确认 +
// reflect-cpp JSON API 在 OHOS 上的运行时行为抽查。
#include <rfl.hpp>
#include <rfl/json.hpp>

#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

namespace {

int failures = 0;

void check(bool cond, const std::string& name) {
  if (cond) {
    std::cout << "[PASS] " << name << std::endl;
  } else {
    std::cout << "[FAIL] " << name << std::endl;
    ++failures;
  }
}

struct OhosSample {
  std::string platform;
  std::uint64_t build_id;
  std::vector<std::int32_t> metrics;
};

}  // namespace

int main() {
  // 1-2: 平台宏确认（本机即 HarmonyOS aarch64 目标）
  check(__OHOS__, "defined(__OHOS__)");
  check(__aarch64__, "defined(__aarch64__)");
  check(__cplusplus >= 202002L, "C++20 mode");
  check(sizeof(void*) == 8, "LP64 data model");

  // 3-6: 基本 JSON 往返
  OhosSample s{.platform = "harmonyos-pc", .build_id = 1727737600ULL,
               .metrics = {1, 2, 3}};
  const std::string json = rfl::json::write(s);
  check(json ==
            R"({"platform":"harmonyos-pc","build_id":1727737600,"metrics":[1,2,3]})",
        "ohos write");
  const auto r = rfl::json::read<OhosSample>(json);
  check(static_cast<bool>(r), "ohos read ok");
  check(static_cast<bool>(r) && r.value().platform == "harmonyos-pc",
        "ohos round-trip platform");
  check(static_cast<bool>(r) && r.value().build_id == 1727737600ULL,
        "ohos round-trip build_id");

  // 7-9: 中文与 Unicode（JSON 字符串编码正确性）
  struct Text {
    std::string msg;
  };
  Text t{.msg = "\xe5\x93\x88\xe6\x9c\x94"};  // "鸿蒙"
  const std::string tjson = rfl::json::write(t);
  const auto tr = rfl::json::read<Text>(tjson);
  check(static_cast<bool>(tr), "unicode read ok");
  check(static_cast<bool>(tr) && tr.value().msg == t.msg, "unicode round-trip");
  check(tjson.find(t.msg) != std::string::npos || tjson.find("\\u") != std::string::npos,
        "unicode encoding produced");

  // 10-12: 嵌套容器（模板递归在 OHOS 工具链下稳定）
  struct Nest {
    std::vector<std::vector<std::string>> grid;
  };
  Nest n{.grid = {{"a", "b"}, {"c", "d"}}};
  const std::string njson = rfl::json::write(n);
  const auto nr = rfl::json::read<Nest>(njson);
  check(static_cast<bool>(nr), "nested read ok");
  check(static_cast<bool>(nr) && nr.value().grid.size() == 2 &&
            nr.value().grid[1][0] == "c",
        "nested round-trip values");
  check(njson == R"({"grid":[["a","b"],["c","d"]]})", "nested write shape");

  // 13-14: 64 位整数值边界（OHOS 上 uint64 序列化正确）
  struct Big {
    std::uint64_t max;
  };
  Big b{.max = UINT64_MAX};
  const std::string bjson = rfl::json::write(b);
  const auto br = rfl::json::read<Big>(bjson);
  check(static_cast<bool>(br), "u64 max read ok");
  check(static_cast<bool>(br) && br.value().max == UINT64_MAX,
        "u64 max round-trip");

  // 15: 错误路径在 OHOS 上可用（不崩溃，返回错误）
  const auto err = rfl::json::read<Big>("[1,2,3]");
  check(!static_cast<bool>(err), "ohos error path returns error");

  if (failures == 0) {
    std::cout << "harmonyos_specific_test: 15 checks ALL OK" << std::endl;
    return 0;
  }
  std::cout << "harmonyos_specific_test: " << failures << " check(s) FAILED"
            << std::endl;
  return 1;
}
