#include <sparsepp/spp.h>

#include <iostream>
#include <string>

#define CHECK(expression) \
    do { \
        if (!(expression)) { \
            std::cerr << "sparsepp consumer test failed: " #expression \
                      << std::endl; \
            return 1; \
        } \
    } while (false)

int main() {
    spp::sparse_hash_map<int, std::string> map;
    const auto inserted = map.emplace(7, "HarmonyOS");
    CHECK(inserted.second);
    CHECK(map.size() == 1);
    CHECK(map.at(7) == "HarmonyOS");
    CHECK(map.find(7) != map.end());

    map[42] = "sparsepp";
    CHECK(map.count(42) == 1);
    map.erase(42);
    CHECK(map.count(42) == 0);

    spp::sparse_hash_set<int> set;
    CHECK(set.insert(7).second);
    CHECK(set.insert(11).second);
    CHECK(!set.insert(7).second);
    CHECK(set.size() == 2);
    CHECK(set.count(7) == 1);
    CHECK(set.find(11) != set.end());

    std::cout << "sparsepp consumer test passed" << std::endl;
    return 0;
}
