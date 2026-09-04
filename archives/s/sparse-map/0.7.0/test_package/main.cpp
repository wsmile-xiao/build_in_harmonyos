// Consumer smoke test using both public containers exported by sparse-map.
#include <iostream>
#include <string>

#include <tsl/sparse_map.h>
#include <tsl/sparse_set.h>

int main() {
    tsl::sparse_map<int, std::string> map;
    map.emplace(7, "seven");

    if (map.size() != 1) {
        std::cerr << "FAIL: expected map size 1, got " << map.size() << '\n';
        return 1;
    }
    if (map.at(7) != "seven") {
        std::cerr << "FAIL: map.at(7) returned the wrong value\n";
        return 1;
    }
    if (!map.contains(7)) {
        std::cerr << "FAIL: map does not contain key 7\n";
        return 1;
    }

    map[11] = "eleven";
    if (map.at(11) != "eleven") {
        std::cerr << "FAIL: operator[] did not store key 11\n";
        return 1;
    }
    if (map.erase(7) != 1) {
        std::cerr << "FAIL: erasing key 7 removed the wrong number of entries\n";
        return 1;
    }
    if (map.contains(7)) {
        std::cerr << "FAIL: erased key 7 is still present\n";
        return 1;
    }

    tsl::sparse_set<int> set;
    set.insert(11);
    set.insert(13);
    if (set.size() != 2) {
        std::cerr << "FAIL: expected set size 2, got " << set.size() << '\n';
        return 1;
    }
    if (!set.contains(11)) {
        std::cerr << "FAIL: set does not contain 11\n";
        return 1;
    }
    if (set.contains(7)) {
        std::cerr << "FAIL: set unexpectedly contains 7\n";
        return 1;
    }
    if (set.erase(11) != 1) {
        std::cerr << "FAIL: erasing 11 removed the wrong number of entries\n";
        return 1;
    }
    if (!set.contains(13)) {
        std::cerr << "FAIL: set should retain key 13 after erasing key 11\n";
        return 1;
    }

    std::cout << "OK: sparse_map and sparse_set consumer checks passed\n";
    return 0;
}
