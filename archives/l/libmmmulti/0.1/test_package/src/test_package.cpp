// test_package for libmmmulti 0.1 — tests mmmultiset and mmiitree APIs.
// mmmultimap excluded (requires sdsl-lite which is not packaged).

#include "mmmultiset.hpp"
#include "mmiitree.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <functional>
#include <string>
#include <vector>
#include <algorithm>
#include <unistd.h>

static int g_failures = 0;

static void check(bool cond, const char* name)
{
    if (cond) {
        std::printf("  PASS: %s\n", name);
    } else {
        std::printf("  FAIL: %s\n", name);
        ++g_failures;
    }
    std::fflush(stdout);
}

// ===========================================================================
// Test 1: mmmultiset — append, index, iteration, unique values
// ===========================================================================
static void test_multiset()
{
    std::printf("[test_multiset]\n");

    std::string filename = "test_multiset.dat";

    // Scope the mset so destructor runs before unlink
    {
        unlink(filename.c_str());
        mmmulti::set<uint64_t> mset(filename);

        // Append values (some duplicates)
        mset.open_writer();
        mset.append(10);
        mset.append(20);
        mset.append(30);
        mset.append(20);
        mset.append(10);
        mset.append(40);
        mset.append(20);
        mset.close_writer();

        // Index (sorts and opens reader)
        mset.index(1);

        // Check total record count
        check(mset.size() == 7,
              "multiset: size() == 7 after inserting 7 values");

        // Collect unique values via for_each_unique_value
        std::vector<uint64_t> unique_vals;
        mset.for_each_unique_value([&](const uint64_t& v) {
            unique_vals.push_back(v);
        });
        std::sort(unique_vals.begin(), unique_vals.end());

        check(unique_vals.size() == 4,
              "multiset: 4 unique values {10,20,30,40}");

        bool values_correct = (unique_vals[0] == 10 &&
                               unique_vals[1] == 20 &&
                               unique_vals[2] == 30 &&
                               unique_vals[3] == 40);
        check(values_correct,
              "multiset: unique values are {10,20,30,40}");
    } // mset destructor runs here, file still exists

    unlink(filename.c_str());
}

// ===========================================================================
// Test 2: mmiitree — add intervals, index, overlap query
// ===========================================================================
static void test_iitree()
{
    std::printf("[test_iitree]\n");

    std::string filename = "test_iitree.dat";

    // Scope the tree so destructor runs before unlink
    {
        unlink(filename.c_str());
        mmmulti::iitree<uint64_t, uint64_t> tree(filename);

        // Add intervals: [1,5), [3,7), [10,15), [20,25)
        tree.open_writer();
        tree.add(1, 5, 100);
        tree.add(3, 7, 200);
        tree.add(10, 15, 300);
        tree.add(20, 25, 400);
        tree.close_writer();

        // Index
        tree.index(1);

        check(tree.size() == 4,
              "iitree: size() == 4 after adding 4 intervals");

        // Query overlap with [4,6) — should hit [1,5) and [3,7)
        std::vector<uint64_t> hit_data;
        tree.overlap(4, 6, [&](const uint64_t& st, const uint64_t& en, const uint64_t& data) {
            (void)st; (void)en;
            hit_data.push_back(data);
        });

        check(hit_data.size() == 2,
              "iitree: overlap([4,6)) returns 2 intervals");

        // Verify the hit data contains 100 and 200
        std::sort(hit_data.begin(), hit_data.end());
        bool hit_ok = (hit_data.size() == 2 && hit_data[0] == 100 && hit_data[1] == 200);
        check(hit_ok,
              "iitree: overlap([4,6)) returns data {100,200}");

        // Query overlap with [12,13) — should hit [10,15) only
        std::vector<uint64_t> hit2;
        tree.overlap(12, 13, [&](const uint64_t& st, const uint64_t& en, const uint64_t& data) {
            (void)st; (void)en;
            hit2.push_back(data);
        });
        check(hit2.size() == 1 && hit2[0] == 300,
              "iitree: overlap([12,13)) returns {300}");

        // Query overlap with [0,1) — should hit nothing
        std::vector<uint64_t> hit3;
        tree.overlap(0, 1, [&](const uint64_t& st, const uint64_t& en, const uint64_t& data) {
            (void)st; (void)en;
            hit3.push_back(data);
        });
        check(hit3.empty(),
              "iitree: overlap([0,1)) returns no intervals");
    } // tree destructor runs here, file still exists

    unlink(filename.c_str());
}

// ===========================================================================
int main()
{
    std::printf("=== libmmmulti 0.1 test_package ===\n");
    std::fflush(stdout);

    test_multiset();
    test_iitree();

    std::printf("\n%s (%d/%d tests passed)\n",
                g_failures == 0 ? "ALL TESTS PASSED" : "TESTS FAILED",
                8 - g_failures, 8);
    return g_failures == 0 ? 0 : 1;
}
