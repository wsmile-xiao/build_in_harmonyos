/*----- test_package consumer test for libdart -----
 *
 * Consumer availability gate: this test simulates a business-layer component
 * that consumes libdart only through its installed public header (<dart.h>)
 * and public C++ API (dart::packet / dart::packet::view). It parses JSON,
 * reads typed values, creates a packet and serializes it back — with
 * observable results — rather than being a print-only shell.
 */
#include <dart.h>

#include <cstdlib>
#include <iostream>
#include <string>

int main() {
  // 1. Parse a JSON document through the public API.
  const std::string input =
      R"({"name":"ohos","version":1,"enabled":true,"tags":["a","b"]})";
  dart::packet pkt;
  try {
    pkt = dart::packet::parse(input, true);
  } catch (dart::parse_error const& e) {
    std::cerr << "FAIL: parse threw: " << e.what() << "\n";
    return 1;
  }

  // 2. Read typed values via the public view interface.
  dart::packet::view view = pkt;
  std::string name = std::string(view["name"].strv());
  bool is_str      = view["name"].is_str();
  auto type        = view["version"].get_type();
  int64_t version  = view["version"].integer();
  bool enabled     = view["enabled"].boolean();
  auto  tags_len   = view["tags"].size();

  std::cout << "parsed name=" << name
            << " is_str=" << (is_str ? "true" : "false")
            << " version_type=" << static_cast<int>(type)
            << " version=" << version
            << " enabled=" << (enabled ? "true" : "false")
            << " tags_len=" << tags_len << "\n";

  if (name != "ohos" || !is_str || version != 1 || !enabled || tags_len != 2) {
    std::cerr << "FAIL: parsed values do not match input\n";
    return 1;
  }

  // 3. Create a packet and serialize it back (public API round-trip).
  dart::packet created = dart::packet::make_object("reply", "ok",
                                                   "code", 200);
  std::string json = created.to_json();
  std::cout << "serialized=" << json << "\n";

  if (json.find("\"reply\":\"ok\"") == std::string::npos ||
      json.find("\"code\":200") == std::string::npos) {
    std::cerr << "FAIL: round-trip serialization mismatch\n";
    return 1;
  }

  std::cout << "PASS: libdart consumer test succeeded\n";
  return 0;
}