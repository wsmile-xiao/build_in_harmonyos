#include <json/json.h>

#include <iostream>
#include <memory>
#include <string>

namespace {
int failures = 0;

void expect(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "FAIL: " << message << '\n';
    ++failures;
  }
}

bool parse(const std::string& document, Json::Value* value,
           std::string* errors) {
  Json::CharReaderBuilder builder;
  std::unique_ptr<Json::CharReader> reader(builder.newCharReader());
  expect(reader.get() != nullptr, "CharReaderBuilder creates a reader");
  return reader && reader->parse(document.data(),
                                 document.data() + document.size(), value,
                                 errors);
}
} // namespace

int main() {
  const std::string input =
      R"({"id":"redex","count":2,"items":["boost","jsoncpp"]})";
  Json::Value root;
  std::string errors;
  expect(parse(input, &root, &errors), "input document parses");
  expect(errors.empty(), "valid input has no parse errors");
  expect(root["id"].asString() == "redex", "string member is available");
  expect(root["count"].asInt() == 2, "numeric member is available");
  expect(root["items"].size() == 2, "array members are available");

  root["platform"] = "HarmonyOS";
  Json::StreamWriterBuilder writer;
  writer["indentation"] = "";
  const std::string output = Json::writeString(writer, root);
  expect(output.find("\"platform\":\"HarmonyOS\"") != std::string::npos,
         "writer serializes the added platform member");

  Json::Value round_trip;
  errors.clear();
  expect(parse(output, &round_trip, &errors), "serialized output reparses");
  expect(errors.empty(), "round-trip output has no parse errors");
  expect(round_trip["platform"].asString() == "HarmonyOS",
         "round trip preserves the platform member");

  if (failures != 0) {
    return 1;
  }
  std::cout << "JsonCpp integration consumer: PASS\n";
  return 0;
}
