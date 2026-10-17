#include <darts.h>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <iostream>
#include <vector>

int main() {
    std::cout << "Darts version: " << DARTS_VERSION << std::endl;

    // 1. Build a tiny trie from 5 ASCII keys
    std::vector<std::string> words = {"ALICE", "BOB", "HE", "HECTOR", "HELLO"};
    std::vector<const char*> keys;
    std::vector<std::string> storage = words;
    for (auto &s : storage) keys.push_back(s.c_str());

    // Optional values: use 0..n as values
    std::vector<int> values;
    for (size_t i = 0; i < keys.size(); ++i) values.push_back(static_cast<int>(i));

    Darts::DoubleArray da;
    int ret = da.build(keys.size(), keys.data(), nullptr, values.data(), nullptr);
    if (ret != 0) {
        std::cerr << "build failed: " << ret << std::endl;
        return 1;
    }
    std::cout << "build ok, size=" << da.size() << " nonzero=" << da.nonzero_size() << std::endl;
    if (da.size() == 0 || da.nonzero_size() == 0) {
        std::cerr << "size check failed" << std::endl;
        return 2;
    }

    // 2. exactMatchSearch - present key
    Darts::DoubleArray::value_type result = -1;
    da.exactMatchSearch("BOB", result);
    std::cout << "exactMatchSearch BOB -> value " << result << std::endl;
    if (result < 0) {
        std::cerr << "exactMatchSearch BOB should succeed" << std::endl;
        return 3;
    }

    // absent key should fail
    result = -1;
    da.exactMatchSearch("UNKNOWN", result);
    std::cout << "exactMatchSearch UNKNOWN -> value " << result << std::endl;
    if (result >= 0) {
        std::cerr << "exactMatchSearch UNKNOWN should fail" << std::endl;
        return 4;
    }

    // 3. commonPrefixSearch on "HELLO WORLD" should find HE (0 or 2) and HELLO
    Darts::DoubleArray::result_pair_type results[16];
    size_t n = da.commonPrefixSearch("HELLO", results, 16);
    std::cout << "commonPrefixSearch HELLO -> n=" << n << std::endl;
    for (size_t i = 0; i < n; ++i) {
        std::cout << "  result[" << i << "] value=" << results[i].value << " len=" << results[i].length << std::endl;
    }
    if (n == 0) {
        std::cerr << "commonPrefixSearch should find at least one" << std::endl;
        return 5;
    }

    // 4. save/open round-trip
    const char *tmpfile = "darts_test.dar";
    if (da.save(tmpfile) != 0) {
        std::cerr << "save failed" << std::endl;
        return 6;
    }
    Darts::DoubleArray da2;
    if (da2.open(tmpfile) != 0) {
        std::cerr << "open failed" << std::endl;
        return 7;
    }
    Darts::DoubleArray::value_type result2 = -1;
    da2.exactMatchSearch("HE", result2);
    std::cout << "after open: exactMatchSearch HE -> value " << result2 << std::endl;
    if (result2 < 0) {
        std::cerr << "open check failed" << std::endl;
        return 8;
    }
    std::remove(tmpfile);

    // 5. traverse-like check: ensure ALICE is found via prefix search on ALICE
    n = da.commonPrefixSearch("ALICE", results, 16);
    bool found_alice = false;
    for (size_t i = 0; i < n; ++i) {
        if (results[i].length == 5) found_alice = true;
    }
    if (!found_alice) {
        std::cerr << "ALICE prefix search failed" << std::endl;
        return 9;
    }

    std::cout << "All darts checks passed" << std::endl;
    return 0;
}
