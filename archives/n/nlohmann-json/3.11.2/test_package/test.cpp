#include <nlohmann/json.hpp>
#include <cassert>
#include <iostream>
#include <string>

int main() {
    // Test 1: Create and serialize JSON
    nlohmann::json j;
    j["name"] = "nlohmann-json";
    j["version"] = "3.11.2";
    j["platform"] = "HarmonyOS";
    std::string dump = j.dump();
    assert(dump.find("nlohmann-json") != std::string::npos);
    assert(dump.find("3.11.2") != std::string::npos);
    assert(dump.find("HarmonyOS") != std::string::npos);

    // Test 2: Parse JSON
    auto parsed = nlohmann::json::parse(R"({"key": "value", "num": 42})");
    assert(parsed["key"] == "value");
    assert(parsed["num"] == 42);

    // Test 3: Array operations
    nlohmann::json arr = {1, 2, 3, 4, 5};
    assert(arr.size() == 5);
    assert(arr[0] == 1);
    assert(arr[4] == 5);

    // Test 4: Type conversion
    nlohmann::json num_json = 3.14;
    double d = num_json.get<double>();
    assert(d == 3.14);

    std::cout << "All nlohmann-json tests passed!" << std::endl;
    return 0;
}
