// test_package for mdds/3.2.1 — exercises two core data structures
// (flat_segment_tree and trie_map) plus a default-construct smoke test of
// multi_type_vector, with real insert/set/query/erase operations and asserts
// on the results.  Compiled and run on the real OHOS aarch64 clang++.

#include <mdds/flat_segment_tree.hpp>
#include <mdds/trie_map.hpp>
#include <mdds/multi_type_vector.hpp>

#include <cassert>
#include <iostream>
#include <string>

// ---------------------------------------------------------------------------
// flat_segment_tree : insert_back / build_tree / is_tree_valid / query
// ---------------------------------------------------------------------------
static void test_flat_segment_tree()
{
    // Key = position, Value = segment label.
    using fst_type = mdds::flat_segment_tree<int, int>;

    fst_type db(0, 100, -1);  // range [0,100), default value -1

    // insert (set) segments.
    db.insert_back(10, 30, 1);   // [10,30) -> 1
    db.insert_back(30, 50, 2);   // [30,50) -> 2
    db.insert_back(70, 90, 3);   // [70,90) -> 3

    // build the tree index that powers point queries.
    db.build_tree();
    assert(db.is_tree_valid());

    // leaf_size() counts the leaf nodes (segments + boundaries).
    auto leaf_count = db.leaf_size();
    assert(leaf_count >= 4);

    // iterate segments via begin_segment()/end_segment() — each segment value
    // has .start, .end, and .value members.
    bool found_1 = false, found_2 = false, found_3 = false, found_default = false;
    for (auto it = db.begin_segment(); it != db.end_segment(); ++it) {
        if (it->value == 1) found_1 = true;
        if (it->value == 2) found_2 = true;
        if (it->value == 3) found_3 = true;
        if (it->value == -1) found_default = true;
    }
    assert(found_1);
    assert(found_2);
    assert(found_3);
    assert(found_default);

    std::cout << "[flat_segment_tree] leaf_size=" << leaf_count
              << " — insert/query OK\n";
}

// ---------------------------------------------------------------------------
// trie_map : insert / find / query / erase
// ---------------------------------------------------------------------------
static void test_trie_map()
{
    // String-keyed trie storing int values.
    using tm_type = mdds::trie_map<std::string, int>;
    tm_type tm;

    // insert (set).
    tm.insert("apple", 1);
    tm.insert("application", 2);
    tm.insert("apply", 3);
    tm.insert("banana", 10);
    tm.insert("band", 20);

    // query via find — iterator's operator->() yields a ref_pair whose
    // .second member is the stored value.
    auto it_apple = tm.find("apple");
    assert(it_apple != tm.end());
    assert(it_apple->second == 1);

    auto it_band = tm.find("band");
    assert(it_band != tm.end());
    assert(it_band->second == 20);

    // query a non-existent key.
    auto it_missing = tm.find("cherry");
    assert(it_missing == tm.end());

    // size reflects inserts.
    assert(tm.size() == 5);
    assert(!tm.empty());

    // erase by key (pointer + length) — trie_map::erase takes
    // (const key_unit_type* key, size_type len).
    std::string apple_key = "apple";
    tm.erase(apple_key.data(), apple_key.size());
    assert(tm.size() == 4);
    assert(tm.find("apple") == tm.end());

    // the other keys are unaffected.
    assert(tm.find("application") != tm.end());
    assert(tm.find("banana") != tm.end());

    // clear.
    tm.clear();
    assert(tm.empty());
    assert(tm.size() == 0);

    std::cout << "[trie_map] insert/find/erase/clear OK\n";
}

// ---------------------------------------------------------------------------
// multi_type_vector: default-construct smoke (header compiles + constructs)
// ---------------------------------------------------------------------------
static void test_headers_compile()
{
    // multi_type_vector is a template alias with a default Traits parameter;
    // default-construct to confirm the header is usable on OHOS.
    mdds::multi_type_vector<> v;
    (void)v;
    std::cout << "[headers] multi_type_vector default-constructs OK\n";
}

int main()
{
    test_flat_segment_tree();
    test_trie_map();
    test_headers_compile();

    std::cout << "All mdds test_package assertions passed.\n";
    return 0;
}
