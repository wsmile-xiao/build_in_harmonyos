// test_package consumer test for tsl-hat-trie 0.6.0 (header-only).
// Exercises the actual public API: htrie_map insert/at/prefix search and
// htrie_set insert/count, compiled as a HarmonyOS/consumer target.
#include <tsl/htrie_map.h>
#include <tsl/htrie_set.h>

#include <cstdio>
#include <string>
#include <vector>

int main() {
    int failures = 0;

    // htrie_map: insert + exact find + prefix range
    tsl::htrie_map<char, int> map;
    map["apple"] = 1;
    map["app"] = 2;
    map["apricot"] = 3;

    if (map.at("apple") != 1) { std::printf("FAIL: at(apple)\n"); ++failures; }
    if (map.at("app") != 2) { std::printf("FAIL: at(app)\n"); ++failures; }
    if (map.size() != 3) { std::printf("FAIL: size\n"); ++failures; }

    std::vector<std::string> prefix;
    auto range = map.equal_prefix_range("ap");
    for (auto it = range.first; it != range.second; ++it) {
        prefix.emplace_back(it.key());
    }
    // "app", "apple", "apricot" all share the "ap" prefix
    if (prefix.size() != 3) {
        std::printf("FAIL: equal_prefix_range size=%zu\n", prefix.size());
        ++failures;
    }

    // htrie_set: insert + count
    tsl::htrie_set<char> set;
    set.insert("hello");
    set.insert("help");
    if (set.count("hello") != 1) { std::printf("FAIL: set count hello\n"); ++failures; }
    if (set.count("nope") != 0) { std::printf("FAIL: set count nope\n"); ++failures; }

    if (failures == 0) {
        std::printf("tsl-hat-trie test_package OK: htrie_map/htrie_set API verified\n");
        return 0;
    }
    std::printf("tsl-hat-trie test_package FAILURES: %d\n", failures);
    return 1;
}
