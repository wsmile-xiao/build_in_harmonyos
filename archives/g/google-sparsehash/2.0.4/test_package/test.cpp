#include <google/dense_hash_map>
#include <google/dense_hash_set>
#include <google/sparse_hash_map>
#include <google/sparse_hash_set>
#include <sparsehash/dense_hash_map>
#include <sparsehash/sparse_hash_map>

#include <iostream>
#include <string>
#include <utility>

// Counts assertions explicitly: every CHECK that runs increments g_checks.
static int g_checks = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (!(cond)) {                                       \
            std::cerr << "FAILED: " << msg << std::endl;      \
            return 1;                                        \
        }                                                    \
        ++g_checks;                                          \
    } while (0)

static int test_sparse_hash_map() {
    google::sparse_hash_map<int, std::string> sparse;
    sparse.set_deleted_key(-1);
    sparse[7] = "HarmonyOS";
    sparse[42] = "sparsehash";
    sparse[100] = "google";

    CHECK(sparse.size() == 3, "sparse_hash_map size after inserts");
    google::sparse_hash_map<int, std::string>::iterator found = sparse.find(42);
    CHECK(found != sparse.end(), "sparse_hash_map find(42)");
    CHECK(found->second == "sparsehash", "sparse_hash_map mapped value");
    CHECK(sparse.count(7) == 1, "sparse_hash_map count(7)");
    CHECK(sparse.count(999) == 0, "sparse_hash_map count of absent key");

    std::pair<google::sparse_hash_map<int, std::string>::iterator, bool> ins =
        sparse.insert(std::make_pair(7, "again"));
    CHECK(!ins.second, "sparse_hash_map duplicate insert rejected");
    CHECK(ins.first->second == "HarmonyOS", "sparse_hash_map insert keeps old value");

    CHECK(sparse.erase(42) == 1, "sparse_hash_map erase returns 1");
    CHECK(sparse.find(42) == sparse.end(), "sparse_hash_map erased key gone");
    CHECK(sparse.size() == 2, "sparse_hash_map size after erase");

    long sum_keys = 0;
    for (google::sparse_hash_map<int, std::string>::const_iterator it = sparse.begin();
         it != sparse.end(); ++it) {
        sum_keys += it->first;
        CHECK(!it->second.empty(), "sparse_hash_map iterated value non-empty");
    }
    CHECK(sum_keys == 107, "sparse_hash_map iteration visits exactly keys 7 and 100");

    google::sparse_hash_map<int, std::string>::iterator probe = sparse.find(7);
    probe->second = "mutated";
    CHECK(sparse[7] == "mutated", "sparse_hash_map mutate via iterator");

    sparse.resize(2048);
    CHECK(sparse.size() == 2, "sparse_hash_map size preserved across resize");
    CHECK(sparse.find(100)->second == "google", "sparse_hash_map lookup after resize");
    return 0;
}

static int test_dense_hash_map() {
    google::dense_hash_map<int, int> dense;
    // dense containers require an empty key before any insertion.
    dense.set_empty_key(-1);
    dense.set_deleted_key(-2);
    dense[1] = 10;
    dense[2] = 20;
    dense[3] = 30;

    CHECK(dense.size() == 3, "dense_hash_map size after inserts");
    CHECK(dense[1] + dense[2] + dense[3] == 60, "dense_hash_map operator[] values");
    CHECK(dense.find(2) != dense.end() && dense.find(2)->second == 20,
          "dense_hash_map find(2)");
    CHECK(dense.count(999) == 0, "dense_hash_map count of absent key");

    CHECK(dense.erase(2) == 1, "dense_hash_map erase returns 1");
    CHECK(dense.find(2) == dense.end(), "dense_hash_map erased key gone");
    CHECK(dense.count(2) == 0, "dense_hash_map count after erase");
    CHECK(dense.size() == 2, "dense_hash_map size after erase");

    long sum = 0;
    int visited = 0;
    for (google::dense_hash_map<int, int>::const_iterator it = dense.begin();
         it != dense.end(); ++it) {
        sum += it->second;
        ++visited;
    }
    CHECK(visited == 2, "dense_hash_map iteration visits only live entries");
    CHECK(sum == 40, "dense_hash_map iteration sum over live entries");

    dense.clear();
    CHECK(dense.empty(), "dense_hash_map clear empties the map");
    return 0;
}

static int test_sparse_and_dense_hash_sets() {
    google::sparse_hash_set<int> sset;
    sset.set_deleted_key(-1);
    for (int i = 0; i < 100; i += 10) {
        sset.insert(i);
    }
    CHECK(sset.size() == 10, "sparse_hash_set size after 10 inserts");
    CHECK(sset.find(50) != sset.end(), "sparse_hash_set find(50)");
    CHECK(sset.find(55) == sset.end(), "sparse_hash_set absent key not found");
    CHECK(sset.erase(50) == 1, "sparse_hash_set erase(50)");
    CHECK(sset.find(50) == sset.end(), "sparse_hash_set erased key gone");
    int count = 0;
    for (google::sparse_hash_set<int>::const_iterator it = sset.begin();
         it != sset.end(); ++it) {
        CHECK((*it) % 10 == 0, "sparse_hash_set iterated key is multiple of 10");
        ++count;
    }
    CHECK(count == 9, "sparse_hash_set iteration visits 9 remaining keys");

    google::dense_hash_set<int> dset;
    dset.set_empty_key(-1);
    dset.set_deleted_key(-2);
    for (int i = 5; i < 100; i += 10) {
        dset.insert(i);
    }
    CHECK(dset.size() == 10, "dense_hash_set size after 10 inserts");
    CHECK(dset.find(45) != dset.end(), "dense_hash_set find(45)");
    CHECK(dset.erase(45) == 1, "dense_hash_set erase(45)");
    CHECK(dset.count(45) == 0, "dense_hash_set count after erase");
    int dcount = 0;
    for (google::dense_hash_set<int>::const_iterator it = dset.begin();
         it != dset.end(); ++it) {
        CHECK(*it % 10 == 5, "dense_hash_set iterated key ends in 5");
        ++dcount;
    }
    CHECK(dcount == 9, "dense_hash_set iteration visits 9 remaining keys");
    return 0;
}

static int test_sparse_hash_map_sparse_hashtable() {
    // sparse_hash_map is backed by sparsehashtable/sparsetable; exercise
    // resizing so the sparse storage group logic runs on OHOS.
    google::sparse_hash_map<int, int> m;
    m.set_deleted_key(-1);
    for (int i = 0; i < 1000; ++i) {
        m[i] = i * 3;
    }
    CHECK(m.size() == 1000, "sparse_hash_map size after 1000 inserts");
    CHECK(m.bucket_count() >= 1000, "sparse_hash_map bucket_count grew");

    for (int i = 0; i < 1000; i += 2) {
        CHECK(m.erase(i) == 1, "sparse_hash_map bulk erase");
    }
    CHECK(m.size() == 500, "sparse_hash_map size after bulk erase");
    long sum = 0;
    for (google::sparse_hash_map<int, int>::const_iterator it = m.begin();
         it != m.end(); ++it) {
        CHECK(it->second == it->first * 3, "sparse_hash_map value invariant");
        sum += it->first;
    }
    CHECK(sum == 250000, "sparse_hash_map odd keys sum after bulk erase");
    return 0;
}

int main() {
    if (test_sparse_hash_map() != 0) return 1;
    if (test_dense_hash_map() != 0) return 2;
    if (test_sparse_and_dense_hash_sets() != 0) return 3;
    if (test_sparse_hash_map_sparse_hashtable() != 0) return 4;

    std::cout << "google-sparsehash consumer test passed (" << g_checks
              << " checks)" << std::endl;
    return 0;
}
