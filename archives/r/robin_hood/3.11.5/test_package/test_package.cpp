// test_package for robin_hood 3.11.5 — real API usage (R34)
// Inserts/lookups into robin_hood::unordered_map and unordered_set
// and verifies actual values, not just a print-only smoke test.
#include <cstdio>
#include <string>

#include <robin_hood.h>

int main() {
    robin_hood::unordered_map<std::string, int> m;
    m["answer"] = 42;
    m["robin"] = 1;
    m["hood"] = 2;

    if (m.size() != 3) {
        std::fprintf(stderr, "FAIL: map size=%zu expected 3\n", m.size());
        return 1;
    }
    auto it = m.find("answer");
    if (it == m.end() || it->second != 42) {
        std::fprintf(stderr, "FAIL: lookup 'answer' failed\n");
        return 1;
    }

    robin_hood::unordered_set<int> s;
    for (int i = 0; i < 1000; ++i) {
        s.insert(i);
    }
    if (s.size() != 1000) {
        std::fprintf(stderr, "FAIL: set size=%zu expected 1000\n", s.size());
        return 1;
    }
    if (s.count(999) != 1 || s.count(-1) != 0) {
        std::fprintf(stderr, "FAIL: set membership wrong\n");
        return 1;
    }

    std::printf("OK: robin_hood map(3)+set(1000) verified\n");
    return 0;
}
