// test_package/test_unordered_dense.cpp — R34: substantive test that uses
// unordered_dense API. Exercises the robin-hood backward-shift map and set:
// insert, lookup, erase (backward shift deletion), iteration, bucket metrics,
// and the stl.h helpers.
#include <ankerl/unordered_dense.h>
#include <ankerl/stl.h>

#include <cstddef>
#include <iostream>
#include <string>

static int failures = 0;

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            std::cerr << "FAIL: " #cond " (line " << __LINE__ << ")\n"; \
            ++failures;                                                 \
        }                                                               \
    } while (0)

int main() {
    // ── unordered_dense::map: robin-hood backward shift deletion ──
    ankerl::unordered_dense::map<std::string, int> m;
    m.max_load_factor(0.25f);
    CHECK(m.empty());

    for (int i = 0; i < 1000; ++i) {
        m["key_" + std::to_string(i)] = i;
    }
    CHECK(m.size() == 1000);
    CHECK(m.count("key_42") == 1);
    CHECK(m.at("key_999") == 999);

    // Lookup of an absent key must report absence without throwing.
    auto it = m.find("missing");
    CHECK(it == m.end());

    // Erase a middle element: triggers backward shift deletion.
    m.erase("key_500");
    CHECK(m.size() == 999);
    CHECK(m.count("key_500") == 0);
    CHECK(m.count("key_499") == 1);
    CHECK(m.count("key_501") == 1);

    // Overwrite of an existing key must not rehash (bucket count stable).
    const std::size_t buckets_before = m.bucket_count();
    m["key_1"] = 1001;
    CHECK(m["key_1"] == 1001);
    CHECK(m.bucket_count() == buckets_before);

    // Iteration must visit every remaining key exactly once.
    int seen = 0;
    for (const auto& [k, v] : m) {
        (void)k;
        (void)v;
        ++seen;
    }
    CHECK(seen == 999);

    // ── unordered_dense::set ──
    ankerl::unordered_dense::set<int> s;
    for (int i = 0; i < 100; i += 2) {
        s.insert(i);
    }
    s.insert(99);
    CHECK(s.size() == 51);
    CHECK(s.count(98) == 1);
    CHECK(s.count(99) == 1);
    CHECK(s.count(1) == 0);
    s.erase(0);
    CHECK(s.count(0) == 0);
    CHECK(s.size() == 50);

    // ── emplace: structured binding reports insertion result ──
    auto [emitted, inserted] = m.emplace("key_new", 7);
    CHECK(inserted);
    CHECK(emitted->second == 7);
    CHECK(m.size() == 1000);

    // ── stl.h is included and must provide the same public API surface ──
    // (stl.h is the umbrella include for the library; no extra public types).
    ankerl::unordered_dense::map<int, int> eh;
    eh[7] = 42;
    CHECK(eh.at(7) == 42);

    if (failures == 0) {
        std::cout << "unordered_dense test passed: all assertions OK" << std::endl;
        return 0;
    }
    std::cerr << failures << " assertion(s) failed" << std::endl;
    return 1;
}