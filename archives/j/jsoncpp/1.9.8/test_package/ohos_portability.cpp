#include <json/json.h>

#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <string>

#if defined(JSONCPP_TEST_EXPECT_OHOS) && !defined(__OHOS__)
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
  expect(std::string(Json::version()) == JSONCPP_VERSION_STRING,
         "runtime and header versions match");

#if defined(JSONCPP_TEST_EXPECT_OHOS)
  expect(sizeof(void*) == 8, "HarmonyOS PC consumer is 64-bit");
#endif

  const Json::UInt64 maximum = std::numeric_limits<Json::UInt64>::max();
  Json::Value value(maximum);
  expect(value.isUInt64(), "maximum UInt64 keeps its JsonCpp type");
  expect(value.asUInt64() == maximum,
         "maximum UInt64 survives the value conversion");

  const std::string escaped = R"({"text":"\u4f60\u597d"})";
  Json::CharReaderBuilder builder;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  Json::Value document;
  std::string errors;
  expect(reader && reader->parse(escaped.data(), escaped.data() + escaped.size(),
                                 &document, &errors),
         "escaped Unicode parses on HarmonyOS");
  expect(errors.empty(), "escaped Unicode has no parse errors");
  expect(document["text"].isString() && !document["text"].asString().empty(),
         "escaped Unicode produces a non-empty UTF-8 string");

  if (failures != 0) {
    return 1;
  }
  std::cout << "JsonCpp HarmonyOS portability consumer: PASS\n";
  return 0;
}
