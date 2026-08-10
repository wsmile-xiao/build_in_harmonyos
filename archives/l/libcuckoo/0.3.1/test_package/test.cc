// Test program for libcuckoo — verifies header-only library functionality
// Uses cuckoohash_map to insert, find, and verify concurrent hash table operations
#include <libcuckoo/cuckoohash_map.hh>
#include <iostream>
#include <string>
#include <cstdlib>

int main(void) {
    libcuckoo::cuckoohash_map<int, std::string> map;

    // Insert key-value pairs
    map.insert(1, "hello");
    map.insert(2, "world");
    map.insert(3, "libcuckoo");

    // Verify finds
    std::string val;
    bool ok = true;

    if (!map.find(1, val) || val != "hello") {
        std::cerr << "FAIL: key 1 expected 'hello', got '" << val << "'" << std::endl;
        ok = false;
    }
    if (!map.find(2, val) || val != "world") {
        std::cerr << "FAIL: key 2 expected 'world', got '" << val << "'" << std::endl;
        ok = false;
    }
    if (!map.find(3, val) || val != "libcuckoo") {
        std::cerr << "FAIL: key 3 expected 'libcuckoo', got '" << val << "'" << std::endl;
        ok = false;
    }
    if (map.find(99, val)) {
        std::cerr << "FAIL: key 99 should not exist" << std::endl;
        ok = false;
    }

    // Verify table size
    if (map.size() != 3) {
        std::cerr << "FAIL: size expected 3, got " << map.size() << std::endl;
        ok = false;
    }

    // Test erase
    map.erase(2);
    if (map.find(2, val)) {
        std::cerr << "FAIL: key 2 should have been erased" << std::endl;
        ok = false;
    }
    if (map.size() != 2) {
        std::cerr << "FAIL: size after erase expected 2, got " << map.size() << std::endl;
        ok = false;
    }

    // Test update
    map.update(1, "updated");
    map.find(1, val);
    if (val != "updated") {
        std::cerr << "FAIL: key 1 after update expected 'updated', got '" << val << "'" << std::endl;
        ok = false;
    }

    if (ok) {
        std::cout << "All libcuckoo tests passed!" << std::endl;
        return 0;
    } else {
        return 1;
    }
}
