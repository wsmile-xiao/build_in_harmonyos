// Consumer test for tsl-hopscotch-map 2.4.0 (header-only C++17).
// Exercises hopscotch_map insert/lookup/erase and hopscotch_set insert/count.
// Returns non-zero on any mismatch so test() exit code reflects correctness.
#include <cstddef>
#include <iostream>
#include <string>

#include <tsl/hopscotch_map.h>
#include <tsl/hopscotch_set.h>

int main() {
    // --- hopscotch_map ---
    tsl::hopscotch_map<int, std::string> map;
    map.insert({1, "one"});
    map.insert({2, "two"});

    if (map.size() != 2) {
        std::cerr << "FAIL: map size expected 2, got " << map.size() << std::endl;
        return 1;
    }
    auto it = map.find(1);
    if (it == map.end() || it->second != "one") {
        std::cerr << "FAIL: map.find(1) != one" << std::endl;
        return 1;
    }
    map.erase(1);
    if (map.contains(1) || map.size() != 1) {
        std::cerr << "FAIL: erase(1) did not remove entry" << std::endl;
        return 1;
    }

    // --- hopscotch_set ---
    tsl::hopscotch_set<int> set;
    set.insert(10);
    set.insert(20);
    if (set.size() != 2 || !set.contains(10) || set.contains(30)) {
        std::cerr << "FAIL: hopscotch_set insert/contains mismatch" << std::endl;
        return 1;
    }

    std::cout << "tsl-hopscotch-map consumer test PASSED (map+set)" << std::endl;
    return 0;
}
