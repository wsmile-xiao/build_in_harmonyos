#include <json/json.h>

#include <iostream>
#include <string>

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
  Json::Value root;
  root["answer"] = 42;
  root["enabled"] = true;
  root["tags"].append("harmonyos");
  root["tags"].append("jsoncpp");

  expect(root.isObject(), "root is an object");
  expect(root["answer"].isInt(), "answer is an integer");
  expect(root["answer"].asInt() == 42, "answer value is retained");
  expect(root["enabled"].asBool(), "boolean value is retained");
  expect(root["tags"].isArray(), "tags is an array");
  expect(root["tags"].size() == 2, "array append preserves both entries");
  expect(root["tags"][0].asString() == "harmonyos",
         "first array value is retained");
  expect(root.get("missing", "fallback").asString() == "fallback",
         "missing member uses the supplied default");

  if (failures != 0) {
    return 1;
  }
  std::cout << "JsonCpp unit consumer: PASS\n";
  return 0;
}
