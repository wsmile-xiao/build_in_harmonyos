#include <cassert>
#include <cstddef>
#include <cstdio>
#include <string>
#include <unordered_map>

// Real consumer test: include and exercise the robin-hood-hashing API
#include "robin_hood.h"

int main() {
    // unordered_map: insert / find / erase round trip
    robin_hood::unordered_map<std::string, int> map;
    map.emplace("answer", 42);
    map.emplace("pi", 3);
    auto it = map.find("answer");
    assert(it != map.end() && it->second == 42);
    assert(map.size() == 2);
    map.erase("pi");
    assert(map.size() == 1);

    // unordered_set: insert / count
    robin_hood::unordered_set<int> set;
    for (int i = 0; i < 100; ++i) {
        set.insert(i);
    }
    assert(set.count(42) == 1);
    assert(set.count(101) == 0);

    std::printf("test robin-hood-hashing 3.11.5: OK (map=%zu set=%zu)\n",
                map.size(), set.size());
    return 0;
}
