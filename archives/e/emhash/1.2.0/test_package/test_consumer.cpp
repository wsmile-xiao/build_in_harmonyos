// test_consumer.cpp — emhash 1.2.0 consumer use case (public API only)
// A real third-party consumer: includes the installed public headers
// emhash/hash_table8.hpp and uses emhash8::HashMap as a drop-in
// std::unordered_map replacement. Every operation is asserted so a
// regression produces a non-zero exit code.
#include <cassert>
#include <iostream>
#include <string>
#include <utility>
#include "emhash/hash_table8.hpp"

int main() {
    emhash8::HashMap<int, std::string> map;

    // Insert
    map[1] = "hello";
    map[2] = "world";
    map.insert({3, "emhash"});

    // Lookup
    assert(map[1] == "hello");
    assert(map[2] == "world");

    // Find / contains / count
    auto it = map.find(3);
    assert(it != map.end());
    assert(it->second == "emhash");
    assert(map.contains(3));
    assert(map.count(3) == 1);
    assert(!map.contains(99));

    // Iterate (structured bindings)
    size_t n = 0;
    for (auto& [k, v] : map) {
        (void)k; (void)v;
        ++n;
    }
    assert(n == map.size());

    // Size and erase
    assert(map.size() == 3);
    map.erase(2);
    assert(map.size() == 2);
    assert(!map.contains(2));

    // at() with exception path
    try {
        (void)map.at(2);
        assert(false && "at() should throw for missing key");
    } catch (const std::out_of_range&) {
    }

    std::cout << "consumer: emhash8::HashMap OK, size=" << map.size()
              << " [1]=hello [3]=emhash" << std::endl;
    return 0;
}
