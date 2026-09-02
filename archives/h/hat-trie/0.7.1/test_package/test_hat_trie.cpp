#include <tsl/htrie_map.h>
#include <tsl/htrie_set.h>

#include <iostream>
#include <iterator>

#define CHECK(expression) \
    do { \
        if (!(expression)) { \
            std::cerr << "hat-trie consumer test failed: " #expression \
                      << std::endl; \
            return 1; \
        } \
    } while (false)

int main() {
    tsl::htrie_map<char, int> map;
    auto inserted = map.insert("apple", 1);
    CHECK(inserted.second);
    CHECK(map.size() == 1);

    map["apricot"] = 2;
    map["banana"] = 3;
    map["band"] = 4;
    CHECK(map.at("apple") == 1);
    CHECK(map.find("missing") == map.end());

    auto prefix = map.equal_prefix_range("ap");
    CHECK(std::distance(prefix.first, prefix.second) == 2);
    auto longest = map.longest_prefix("apricot-pie");
    CHECK(longest != map.end());
    CHECK(longest.key() == "apricot");
    CHECK(map.erase_prefix("ban") == 2);
    CHECK(map.size() == 2);

    tsl::htrie_set<char> set;
    CHECK(set.insert("one").second);
    set.insert("two");
    set.insert("three");
    CHECK(set.count("two") == 1);
    CHECK(set.erase("two") == 1);
    CHECK(set.count("two") == 0);

    std::cout << "hat-trie consumer test passed\n";
    return 0;
}
