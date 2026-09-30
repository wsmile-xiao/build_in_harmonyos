// Consumer test — meojson 5.1.2 on HarmonyOS (OHOS aarch64).
//
// Simulates a business-layer component that consumes meojson only through its
// installed public headers and public API (json::parse, json::value,
// json::array, json::object, serialization). Returns non-zero on any failed
// assertion so the harness fails loudly. This is a real API-exercising test,
// not an include-only stub.
#include <iostream>
#include <string>

#include <meojson/json.hpp>

namespace
{
int failures = 0;

void check(bool cond, const std::string& what)
{
    if (!cond) {
        std::cerr << "FAIL: " << what << std::endl;
        failures++;
    }
}

void test_parse_and_access()
{
    const std::string text = R"({"name":"meojson","version":5.1,"ok":true,"tags":["json","cpp17"],"meta":{"repo":"MistEO/meojson"}})";

    auto parsed = json::parse(text);
    check(parsed.has_value(), "json::parse top-level object");
    if (!parsed) {
        return;
    }

    json::value v = std::move(*parsed);
    check(v.contains("name"), "contains(name)");
    check(v["name"].as_string() == "meojson", "as_string name");
    check(v["version"].as_double() == 5.1, "as_double version");
    check(v["ok"].as_boolean() == true, "as_boolean ok");

    const auto& tags = v["tags"].as_array();
    check(tags.size() == 2, "tags array size");
    check(tags[0].as_string() == "json", "tags[0]");
    check(tags[1].as_string() == "cpp17", "tags[1]");

    const auto& meta = v["meta"].as_object();
    check(meta.contains("repo"), "meta has repo");
    check(meta.at("repo").as_string() == "MistEO/meojson", "meta repo value");
}

void test_build_and_serialize()
{
    json::value obj = {
        { "project", "meojson" },
        { "mode", json::value("rc") },
        { "number", 5 },
        { "pi", 3.1415926 },
        { "flags", json::array { true, false, json::value() } },
    };
    check(obj["project"].as_string() == "meojson", "object init project");
    check(obj["number"].as_integer() == 5, "object init number");

    std::string dumped = obj.dumps(2);
    check(dumped.find("\"project\": \"meojson\"") != std::string::npos, "dumps contains project");

    auto reparsed = json::parse(dumped);
    check(reparsed.has_value(), "reparse dumped json");
    if (reparsed) {
        check((*reparsed)["flags"].as_array().size() == 3, "reparsed flags size");
    }
}

void test_array_object_roundtrip()
{
    json::array arr;
    arr.emplace_back("a");
    arr.emplace_back(2);
    arr.emplace_back(json::object { { "k", "v" } });

    check(arr.size() == 3, "emplace_back size");
    check(arr[1].as_integer() == 2, "array int element");

    std::string dumped = arr.dumps();
    auto reparsed = json::parse(dumped);
    check(reparsed.has_value(), "array roundtrip parse");
    if (reparsed) {
        const auto& back_arr = (*reparsed).as_array();
        const auto& last = back_arr[back_arr.size() - 1];
        check(last.at("k").as_string() == "v", "array roundtrip nested object");
    }
}
} // namespace

int main()
{
    std::cout << "meojson consumer test starting" << std::endl;
    test_parse_and_access();
    test_build_and_serialize();
    test_array_object_roundtrip();

    if (failures == 0) {
        std::cout << "meojson consumer test PASSED" << std::endl;
        return 0;
    }
    std::cerr << "meojson consumer test FAILED with " << failures << " assertion(s)" << std::endl;
    return 1;
}