// Homebrew-equivalent consumer test for robin-map 1.4.1.
// Inserts {1:"one", 2:"two"} into tsl::robin_map, verifies size/lookup, prints.
// Returns non-zero on any mismatch so test() exit code reflects correctness.
#include <iostream>
#include <string>
#include <tsl/robin_map.h>

int main() {
    tsl::robin_map<int, std::string> map;
    map[1] = "one";
    map[2] = "two";

    // Correctness checks (R34: test must genuinely verify, not just run).
    if (map.size() != 2) {
        std::cerr << "FAIL: expected size 2, got " << map.size() << std::endl;
        return 1;
    }
    if (map[1] != "one") {
        std::cerr << "FAIL: map[1] != \"one\", got \"" << map[1] << "\"" << std::endl;
        return 1;
    }
    if (map[2] != "two") {
        std::cerr << "FAIL: map[2] != \"two\", got \"" << map[2] << "\"" << std::endl;
        return 1;
    }

    for (const auto& pair : map) {
        std::cout << pair.first << ": " << pair.second << std::endl;
    }
    return 0;
}
