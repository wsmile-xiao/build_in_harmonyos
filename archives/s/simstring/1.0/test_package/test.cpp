// test_package consumer for simstring 1.0 — header-only API, real assertions.
//
// Builds a small n-gram database with the packaged writer, reopens it with
// the reader and checks exact / cosine / dice retrieval end to end. Returns
// non-zero on the first failed assertion so conan create fails loudly.
#include <cstdlib>
#include <iostream>
#include <iterator>
#include <string>
#include <vector>

#include <simstring/simstring.h>

static int g_asserts = 0;

#define TP_ASSERT(cond, msg)                                        \
    do {                                                            \
        ++g_asserts;                                                \
        if (!(cond)) {                                              \
            std::cerr << "TP FAIL: " << (msg) << std::endl;         \
            return 1;                                               \
        }                                                           \
    } while (0)

static std::vector<std::string> retrieve(simstring::reader &dbr,
                                         const std::string &query,
                                         int measure,
                                         double threshold) {
    std::vector<std::string> out;
    dbr.retrieve(query, measure, threshold, std::back_inserter(out));
    return out;
}

static bool contains(const std::vector<std::string> &v, const std::string &needle,
                     bool exact) {
    for (size_t i = 0; i < v.size(); ++i) {
        if (exact) {
            if (v[i] == needle) return true;
        } else if (v[i].find(needle) != std::string::npos) {
            return true;
        }
    }
    return false;
}

int main() {
    // --- build phase (ngram_generator(3, no begin/end marks)) ---
    simstring::ngram_generator gen(3, false);
    simstring::writer_base<std::string> dbw(gen, "tp_api.db");
    TP_ASSERT(!dbw.fail(), "database writer opens in cwd");
    TP_ASSERT(dbw.insert("Barack Hussein Obama II"), "insert Obama entry");
    TP_ASSERT(dbw.insert("James Gordon Brown"), "insert Brown entry");
    TP_ASSERT(dbw.insert("apple"), "insert apple entry");
    dbw.close();
    TP_ASSERT(!dbw.fail(), "database writer flushes on close");

    // --- retrieve phase ---
    simstring::reader dbr;
    TP_ASSERT(dbr.open("tp_api.db"), "database reader opens");

    // exact match with threshold 1.0 must return the inserted string itself
    std::vector<std::string> r1 =
        retrieve(dbr, "Barack Hussein Obama II", simstring::exact, 1.0);
    TP_ASSERT(contains(r1, "Barack Hussein Obama II", true),
              "exact 1.0 retrieves the self string");

    // cosine 0.6 over a shortened query still hits the Obama entry
    std::vector<std::string> r2 = retrieve(dbr, "Barack Obama", simstring::cosine, 0.6);
    TP_ASSERT(contains(r2, "Obama", false), "cosine 0.6 retrieves Obama entry");

    // dice coefficient over the Brown entry
    std::vector<std::string> r3 =
        retrieve(dbr, "James Gordon Brown", simstring::dice, 0.5);
    TP_ASSERT(contains(r3, "Brown", false), "dice retrieves Brown entry");

    // cosine 1.0 for a disjoint string must not match apple
    std::vector<std::string> r4 = retrieve(dbr, "zzqqxxjjvv", simstring::cosine, 1.0);
    TP_ASSERT(!contains(r4, "apple", false),
              "disjoint query at threshold 1.0 returns no apple");

    // jaccard/overlap measures at least exercise the remaining measure paths
    std::vector<std::string> r5 =
        retrieve(dbr, "apple", simstring::jaccard, 0.3);
    TP_ASSERT(contains(r5, "apple", false), "jaccard retrieves apple");
    std::vector<std::string> r6 =
        retrieve(dbr, "Barack Hussein Obama II", simstring::overlap, 1.0);
    TP_ASSERT(contains(r6, "Obama", false), "overlap retrieves Obama entry");

    std::cout << "simstring header API: " << g_asserts << " assertions OK" << std::endl;
    return 0;
}
