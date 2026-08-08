// parallel-hashmap library — consumer test for parallel-hashmap/2.0.0
//
// Verifies that parallel-hashmap headers can be included and basic APIs work:
//   - phmap::flat_hash_map (drop-in for std::unordered_map)
//   - phmap::flat_hash_set (drop-in for std::unordered_set)
//   - phmap::btree_map / phmap::btree_set
//   - phmap::parallel_flat_hash_map
//   - version macros
//
// Uses explicit CHECK macros instead of assert() so validation works in
// both Debug and Release builds (assert is removed by -DNDEBUG in Release).

#include <cstdlib>
#include <iostream>
#include <string>

#include <parallel_hashmap/phmap.h>
#include <parallel_hashmap/btree.h>

#define CHECK(expr)                                                      \
    do {                                                                 \
        if (!(expr)) {                                                   \
            std::cerr << "FAIL: " << __FILE__ << ":" << __LINE__ << ": " \
                      << #expr << std::endl;                             \
            std::exit(1);                                                \
        }                                                                \
    } while (0)

int main()
{
    // Test 1: flat_hash_map — basic insert and lookup
    phmap::flat_hash_map<std::string, int> map;
    map["apple"] = 1;
    map["banana"] = 2;
    map["cherry"] = 3;
    CHECK(map.size() == 3);
    CHECK(map["apple"] == 1);
    CHECK(map["banana"] == 2);
    CHECK(map["cherry"] == 3);
    std::cout << "PASS: flat_hash_map — insert/lookup OK" << std::endl;

    // Test 2: flat_hash_map — contains and find
    CHECK(map.contains("apple"));
    CHECK(!map.contains("grape"));
    auto it = map.find("banana");
    CHECK(it != map.end());
    CHECK(it->second == 2);
    std::cout << "PASS: flat_hash_map — contains/find OK" << std::endl;

    // Test 3: flat_hash_set — basic operations
    phmap::flat_hash_set<int> set;
    set.insert(10);
    set.insert(20);
    set.insert(30);
    CHECK(set.size() == 3);
    CHECK(set.contains(10));
    CHECK(set.contains(20));
    CHECK(!set.contains(40));
    std::cout << "PASS: flat_hash_set — insert/contains OK" << std::endl;

    // Test 4: flat_hash_set — erase
    set.erase(20);
    CHECK(set.size() == 2);
    CHECK(!set.contains(20));
    std::cout << "PASS: flat_hash_set — erase OK" << std::endl;

    // Test 5: btree_map — ordered map
    phmap::btree_map<int, std::string> bmap;
    bmap[3] = "three";
    bmap[1] = "one";
    bmap[2] = "two";
    CHECK(bmap.size() == 3);
    // btree_map is ordered
    auto bit = bmap.begin();
    CHECK(bit->first == 1);
    CHECK(bit->second == "one");
    ++bit;
    CHECK(bit->first == 2);
    ++bit;
    CHECK(bit->first == 3);
    std::cout << "PASS: btree_map — ordered iteration OK" << std::endl;

    // Test 6: btree_set
    phmap::btree_set<int> bset;
    bset.insert(5);
    bset.insert(3);
    bset.insert(7);
    CHECK(bset.size() == 3);
    CHECK(bset.contains(3));
    CHECK(!bset.contains(4));
    std::cout << "PASS: btree_set — insert/contains OK" << std::endl;

    // Test 7: parallel_flat_hash_map
    phmap::parallel_flat_hash_map<int, int> pmap;
    for (int i = 0; i < 100; ++i) {
        pmap[i] = i * i;
    }
    CHECK(pmap.size() == 100);
    CHECK(pmap[5] == 25);
    CHECK(pmap[9] == 81);
    // iteration over sub-maps
    int count = 0;
    for (const auto& kv : pmap) {
        CHECK(kv.first * kv.first == kv.second);
        ++count;
    }
    CHECK(count == 100);
    std::cout << "PASS: parallel_flat_hash_map — 100 entries OK" << std::endl;

    // Test 8: version macros
    CHECK(PHMAP_VERSION_MAJOR == 2);
    CHECK(PHMAP_VERSION_MINOR == 0);
    CHECK(PHMAP_VERSION_PATCH == 0);
    std::cout << "PASS: version macros OK ("
              << PHMAP_VERSION_MAJOR << "."
              << PHMAP_VERSION_MINOR << "."
              << PHMAP_VERSION_PATCH << ")" << std::endl;

    std::cout << std::endl << "All parallel-hashmap consumer tests PASSED." << std::endl;
    return 0;
}
