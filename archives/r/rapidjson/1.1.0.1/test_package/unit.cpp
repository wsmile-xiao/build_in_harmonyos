#include <rapidjson/document.h>
#include <rapidjson/stringbuffer.h>
#include <rapidjson/writer.h>

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
  const std::string input =
      R"({"id":"redex","count":2,"items":["boost","rapidjson"]})";

  rapidjson::Document document;
  expect(!document.Parse(input.c_str()).HasParseError(),
         "input document parses");
  expect(document.IsObject(), "root is an object");
  expect(document["id"].IsString() &&
             std::string(document["id"].GetString()) == "redex",
         "string member is available");
  expect(document["count"].IsInt() && document["count"].GetInt() == 2,
         "numeric member is available");
  expect(document["items"].IsArray() && document["items"].Size() == 2,
         "array members are available");

  rapidjson::Value platform("HarmonyOS", document.GetAllocator());
  document.AddMember("platform", platform, document.GetAllocator());

  rapidjson::StringBuffer buffer;
  rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
  expect(document.Accept(writer), "writer serializes the document");
  expect(std::string(buffer.GetString()).find("\"platform\":\"HarmonyOS\"") !=
             std::string::npos,
         "writer serializes the added platform member");

  rapidjson::Document round_trip;
  expect(!round_trip.Parse(buffer.GetString()).HasParseError(),
         "serialized output reparses");
  expect(round_trip["platform"].IsString() &&
             std::string(round_trip["platform"].GetString()) == "HarmonyOS",
         "round trip preserves the platform member");

  if (failures != 0) {
    return 1;
  }
  std::cout << "RapidJSON unit consumer: PASS\n";
  return 0;
}
