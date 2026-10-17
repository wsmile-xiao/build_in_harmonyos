#include <tsl/robin_map.h>
#include <iostream>
#include <string>

// Explicit failure checks that stay active under Release/NDEBUG
// (assert would be compiled out). Real tsl::robin_map API usage.
static int check(bool ok, const char* what) {
    if (!ok) {
        std::cerr << "FAIL: " << what << "\n";
        return 1;
    }
    return 0;
}

int main() {
    tsl::robin_map<int, std::string> map;
    map.insert({1, "one"});
    map.insert({2, "two"});

    int failures = 0;
    failures += check(map.size() == 2, "map.size() == 2");
    failures += check(map.at(1) == "one", "map.at(1) == \"one\"");
    failures += check(map.at(2) == "two", "map.at(2) == \"two\"");

    for (const auto& kv : map) {
        std::cout << kv.first << " -> " << kv.second << "\n";
    }

    if (failures != 0) {
        std::cerr << "robin-map consumer smoke test FAILED (" << failures << " check(s))\n";
        return 1;
    }
    std::cout << "robin-map consumer smoke test PASSED\n";
    return 0;
}
