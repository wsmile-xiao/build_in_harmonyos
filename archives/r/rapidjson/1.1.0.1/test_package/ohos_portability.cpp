#include <rapidjson/document.h>

#include <cstdint>
#include <iostream>
#include <string>

#if defined(RAPIDJSON_TEST_EXPECT_OHOS) && !defined(__OHOS__)
#error "HarmonyOS CMake configuration must define __OHOS__"
#endif

namespace {
int failures = 0;

void expect(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "FAIL: " << message << '\n';
    ++failures;
  }
}
} // namespace

int main() {
#if defined(RAPIDJSON_TEST_EXPECT_OHOS)
  expect(sizeof(void*) == 8, "HarmonyOS PC consumer is 64-bit");
#endif

  const std::string escaped = R"({"text":"你好"})";
  rapidjson::Document document;
  expect(!document.Parse(escaped.c_str()).HasParseError(),
         "escaped Unicode parses");
  expect(document["text"].IsString() &&
             !std::string(document["text"].GetString()).empty(),
         "escaped Unicode produces a non-empty UTF-8 string");

  // Full-precision mode keeps int64 boundaries exact.
  const std::string number = R"({"max":9223372036854775807})";
  rapidjson::Document full_precision;
  expect(!full_precision
              .Parse<rapidjson::kParseFullPrecisionFlag>(number.c_str())
              .HasParseError(),
         "int64 boundary parses in full-precision mode");
  expect(full_precision["max"].IsInt64() &&
             full_precision["max"].GetInt64() == INT64_MAX,
         "int64 boundary is exact");

  if (failures != 0) {
    return 1;
  }
  std::cout << "RapidJSON HarmonyOS portability consumer: PASS\n";
  return 0;
}
