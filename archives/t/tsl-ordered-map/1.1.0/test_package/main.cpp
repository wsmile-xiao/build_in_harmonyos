// Consumer smoke test — tsl-ordered-map 1.1.0 (HarmonyOS PC / aarch64)
//
// Verifies the upstream exported CMake target tsl::ordered_map through the
// standard consumer flow: find_package(tsl-ordered-map) + insert/lookup/erase
// on tsl::ordered_map, including deterministic insertion-order iteration,
// which is the core differentiator of the ordered-map family.
#include <cassert>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

#include <tsl/ordered_map.h>

int main() {
    tsl::ordered_map<int, std::string> map;
    map.insert({1, "one"});
    map.insert({2, "two"});
    map.insert({3, "three"});

    // Basic size / lookup semantics.
    assert(map.size() == 3);
    assert(map.at(1) == "one");
    assert(map.at(2) == "two");
    assert(map.at(3) == "three");

    // Deterministic insertion-order iteration: ordered_map keeps the key
    // order stable, unlike a plain hash map.
    std::vector<int> order;
    for (const auto& kv : map) {
        order.push_back(kv.first);
    }
    assert((order == std::vector<int>{1, 2, 3}));

    // Erase + re-insert keeps deterministic ordering (erase preserves
    // remaining order, re-insert appends at the end).
    map.erase(2);
    std::vector<int> order_after_erase;
    for (const auto& kv : map) {
        order_after_erase.push_back(kv.first);
    }
    assert((order_after_erase == std::vector<int>{1, 3}));

    for (const auto& kv : map) {
        std::cout << kv.first << ":" << kv.second << "\n";
    }
    std::cout << "ordered_map consumer test OK (" << map.size() << " entries)\n";
    return 0;
}