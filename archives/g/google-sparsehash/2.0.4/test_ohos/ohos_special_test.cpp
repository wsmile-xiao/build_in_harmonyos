// HarmonyOS PC (OHOS aarch64) special test for google-sparsehash 2.0.4.
//
// Independently exercises the packaged headers through BOTH public include
// trees (sparsehash/ and the legacy google/ compatibility tree) using the
// real OHOS toolchain, plus behaviors important on 64-bit musl/OHOS:
// default float empty/deleted keys, string keys with std::hash, large
// table growth across sparse groups, and dense map rehash after erase.
#include <google/dense_hash_map>
#include <google/sparse_hash_map>
#include <sparsehash/dense_hash_map>
#include <sparsehash/sparse_hash_map>

#include <cstdio>
#include <string>

static int g_checks = 0;

#define CHECK(cond, msg)                                        \
    do {                                                        \
        if (!(cond)) {                                          \
            std::fprintf(stderr, "FAILED: %s\n", msg);          \
            return 1;                                           \
        }                                                       \
        ++g_checks;                                             \
    } while (0)

// T1: legacy google/ include tree, default-constructed value types.
static int t1_legacy_includes() {
    google::dense_hash_map<int, double> d;
    d.set_empty_key(-1);
    d.set_deleted_key(-2);
    d[3] = 1.5;
    CHECK(d.size() == 1 && d[3] == 1.5, "T1 dense insert via google/ header");
    CHECK(d.erase(3) == 1 && d.empty(), "T1 dense erase via google/ header");

    google::sparse_hash_map<int, double> s;
    s[4] = 2.5;
    CHECK(s.find(4) != s.end() && s.find(4)->second == 2.5,
          "T1 sparse lookup via google/ header");
    return 0;
}

// T2: sparsehash/ include tree, std::string keys hashed by std::hash.
static int t2_string_keys() {
    google::sparse_hash_map<std::string, int> m;
    m.set_deleted_key(std::string());
    m["harmony"] = 1;
    m["ohos"] = 2;
    CHECK(m.size() == 2, "T2 size with string keys");
    CHECK(m.find("ohos") != m.end() && m["ohos"] == 2, "T2 string key lookup");
    CHECK(m.erase("harmony") == 1, "T2 string key erase");
    CHECK(m.find("harmony") == m.end(), "T2 erased string key gone");
    google::sparse_hash_map<std::string, int>::const_iterator it = m.begin();
    CHECK(it != m.end() && it->first == "ohos" && it->second == 2,
          "T2 iteration over remaining string entry");
    return 0;
}

// T3: growth across sparse groups (DEFAULT_GROUP_SIZE = 48) exercises
// sparsetable group splitting on OHOS aarch64.
static int t3_group_growth() {
    google::sparse_hash_map<int, int> m;
    m.set_deleted_key(-1);
    for (int i = 0; i < 5000; ++i) {
        m[i * 7] = i;
    }
    CHECK(m.size() == 5000, "T3 5000 inserts");
    long sum = 0;
    for (google::sparse_hash_map<int, int>::const_iterator it = m.begin();
         it != m.end(); ++it) {
        sum += it->second;
    }
    CHECK(sum == 4999L * 5000L / 2, "T3 iteration sum across groups");
    for (int i = 0; i < 5000; i += 3) {
        CHECK(m.erase(i * 7) == 1, "T3 erase during churn");
    }
    CHECK(m.size() == 5000 - (5000 + 2) / 3, "T3 size after churn");
    CHECK(m.find(7 * 4999) != m.end(), "T3 high key survives churn");
    return 0;
}

// T4: dense map insert/erase churn forcing internal resize/rehash, with
// the negative sentinels required by the dense API.
static int t4_dense_rehash() {
    google::dense_hash_map<int, int> d;
    d.set_empty_key(-1);
    d.set_deleted_key(-2);
    for (int i = 0; i < 2000; ++i) {
        d[i] = i;
    }
    CHECK(d.size() == 2000, "T4 dense 2000 inserts");
    for (int i = 0; i < 2000; i += 2) {
        CHECK(d.erase(i) == 1, "T4 dense erase");
    }
    CHECK(d.size() == 1000, "T4 dense size after erases");
    CHECK(d.find(1999) != d.end() && d[1999] == 1999,
          "T4 dense lookup after rehash");
    long sum = 0;
    for (google::dense_hash_map<int, int>::const_iterator it = d.begin();
         it != d.end(); ++it) {
        sum += it->second;
    }
    CHECK(sum == 1000L * 1000L, "T4 dense iteration sum after rehash");
    return 0;
}

int main() {
    if (t1_legacy_includes() != 0) return 1;
    if (t2_string_keys() != 0) return 2;
    if (t3_group_growth() != 0) return 3;
    if (t4_dense_rehash() != 0) return 4;
    std::printf("OHOS special test ALL PASS (%d checks)\n", g_checks);
    return 0;
}
