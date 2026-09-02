// test_jsoncons.cpp — Substantive consumer test for jsoncons
// (Conan L1) — verifies the packaged jsoncons API: object construction,
// serialization round-trip, parsing, and typed access.

#include <jsoncons/json.hpp>
#include <cstdio>
#include <string>

static int failures = 0;
#define CHECK(cond, label) do { \
    if (!(cond)) { std::fprintf(stderr, "FAIL: %s\n", label); failures++; } \
} while (0)

int main() {
    // 1) object construction + member access
    jsoncons::json j;
    j["name"] = "jsoncons";
    j["major"] = 1;
    j["nested"]["enabled"] = true;
    CHECK(j["name"].as<std::string>() == "jsoncons", "object member access");
    CHECK(j["major"].as<int>() == 1, "integer member access");
    CHECK(j["nested"]["enabled"].as<bool>() == true, "nested bool access");

    // 2) serialization round-trip
    std::string s = j.to_string();
    CHECK(s.find("\"name\":\"jsoncons\"") != std::string::npos, "serialization contains key/val");

    // 3) parse back
    jsoncons::json j2 = jsoncons::json::parse(s);
    CHECK(j2["name"].as<std::string>() == "jsoncons", "parse round-trip name");

    // 4) array support
    jsoncons::json arr = jsoncons::json::array();
    arr.push_back(1);
    arr.push_back(2);
    arr.push_back(3);
    CHECK(arr.size() == 3 && arr[2].as<int>() == 3, "array push/access");

    // 5) version info available
    jsoncons::versioning_info ver = jsoncons::version();
    CHECK(ver.major == 1 && ver.minor == 9 && ver.patch == 0, "jsoncons version == 1.9.0");

    if (failures == 0) {
        std::printf("PASS: jsoncons header-only 库链接和核心 API 验证通过\n");
        return 0;
    }
    return 1;
}