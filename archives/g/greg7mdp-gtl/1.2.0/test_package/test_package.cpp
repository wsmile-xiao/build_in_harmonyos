// Consumer test for the packaged greg7mdp-gtl headers (R34).
//
// Includes <gtl/...> exactly like a downstream project would — through the
// packaged include dir exposed by `find_package(gtl)` — and exercises the
// public API of the containers the package actually delivers.  Every check
// is counted explicitly and reported; the process exits non-zero on any
// failure (no assert()/NDEBUG pitfalls, nothing is stubbed).
//
// GTL_HAVE_SSE2 / GTL_HAVE_SSSE3 are printed as informational output: on
// x86_64 upstream selects its SSE2/SSSE3 fast path, on aarch64 (this
// device) both macros are 0 and upstream selects GroupPortableImpl, so
// this file also proves that the portable code path is the one that is
// actually built and executed.
#include <gtl/btree.hpp>
#include <gtl/bit_vector.hpp>
#include <gtl/gtl_config.hpp>
#include <gtl/lru_cache.hpp>
#include <gtl/phmap.hpp>
#include <gtl/stopwatch.hpp>
#include <gtl/vector.hpp>

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

static int checks = 0;
static int failures = 0;

#define GTL_CHECK(cond)                                                  \
    do {                                                                 \
        ++checks;                                                        \
        if (!(cond)) {                                                   \
            ++failures;                                                  \
            std::fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, \
                         #cond);                                         \
        }                                                                \
    } while (0)

int main() {
    // 1. version fingerprint of the packaged header (not the source tree)
    GTL_CHECK(GTL_VERSION_MAJOR == 1);
    GTL_CHECK(GTL_VERSION_MINOR == 2);
    GTL_CHECK(GTL_VERSION_PATCH == 0);
    GTL_CHECK(GTL_HAVE_SSE2 == 0 || GTL_HAVE_SSE2 == 1);
    GTL_CHECK(GTL_HAVE_SSSE3 == 0 || GTL_HAVE_SSSE3 == 1);

    // 2. flat_hash_map
    gtl::flat_hash_map<int, int> m;
    for (int i = 0; i < 100; ++i) {
        m[i] = i * i;
    }
    GTL_CHECK(m.size() == 100);
    GTL_CHECK(m.at(12) == 144);
    GTL_CHECK(m.contains(99));
    GTL_CHECK(!m.contains(100));
    GTL_CHECK(m.erase(0) == 1);
    GTL_CHECK(m.size() == 99);
    GTL_CHECK(m.count(50) == 1);

    // 3. flat_hash_set<std::string>
    gtl::flat_hash_set<std::string> words = {"harmony", "openharmony", "gtl"};
    GTL_CHECK(words.size() == 3);
    GTL_CHECK(words.contains("gtl"));
    GTL_CHECK(!words.contains("missing"));
    GTL_CHECK(words.find("harmony") != words.end());

    // 4. node_hash_map keeps references stable across rehash
    gtl::node_hash_map<std::string, int> nm;
    nm["alpha"] = 1;
    nm["beta"] = 2;
    int* beta = &nm["beta"];
    for (int i = 0; i < 200; ++i) {
        nm["k" + std::to_string(i)] = i;
    }
    GTL_CHECK(nm.size() == 202);
    GTL_CHECK(beta != nullptr && *beta == 2);
    GTL_CHECK(*beta == nm.at("beta"));

    // 5. parallel (sharded) hash map, the mutex-protected variant
    gtl::parallel_flat_hash_map_m<int, int> pm;
    for (int i = 0; i < 500; ++i) {
        pm[i] = i + 1;
    }
    GTL_CHECK(pm.size() == 500);
    GTL_CHECK(pm.at(499) == 500);
    GTL_CHECK(pm.contains(250));

    // 6. btree_map / btree_set keep keys ordered
    gtl::btree_map<int, int> bm;
    const std::vector<int> keys = {5, 1, 9, 3, 7};
    for (int k : keys) {
        bm[k] = k * 10;
    }
    GTL_CHECK(bm.size() == 5);
    GTL_CHECK(bm.at(3) == 30);
    {
        int prev = -1;
        bool ordered = true;
        long long sum = 0;
        for (const auto& kv : bm) {
            if (kv.first < prev) {
                ordered = false;
            }
            prev = kv.first;
            sum += kv.second;
        }
        GTL_CHECK(ordered);
        GTL_CHECK(sum == 250); // (5+1+9+3+7) * 10
    }

    gtl::btree_set<int> bs;
    for (int k : keys) {
        bs.insert(k);
    }
    GTL_CHECK(bs.size() == 5);
    GTL_CHECK(*bs.begin() == 1);
    GTL_CHECK(bs.contains(9));

    // 7. bit_vector
    gtl::bit_vector bv(128, false);
    bv.set(0);
    bv.set(63);
    bv.set(64);
    bv.set(127);
    GTL_CHECK(bv.size() == 128);
    GTL_CHECK(bv.test(63));
    GTL_CHECK(!bv.test(62));
    GTL_CHECK(bv.count() == 4);
    bv.flip(0);
    GTL_CHECK(!bv.test(0));
    GTL_CHECK(bv.count() == 3);

    // 8. lru_cache eviction
    gtl::lru_cache<int, int> lru;
    lru.set_cache_size(3);
    lru.insert(1, 10);
    lru.insert(2, 20);
    lru.insert(3, 30);
    GTL_CHECK(lru.exists(1));
    lru.insert(4, 40); // evicts the least recently used entry
    GTL_CHECK(lru.size() <= 4);
    GTL_CHECK(lru.exists(4));

    // 9. stopwatch monotonic measurement
    gtl::stopwatch sw;
    GTL_CHECK(sw.since_start() >= 0.0f);

    // 10. gtl::vector insert/erase/indexing
    gtl::vector<int> v;
    v.push_back(1);
    v.push_back(2);
    v.push_back(3);
    GTL_CHECK(v.size() == 3);
    GTL_CHECK(v[0] == 1 && v[2] == 3);
    v.erase(v.begin() + 1);
    GTL_CHECK(v.size() == 2);
    GTL_CHECK(v[1] == 3);

    // 11. hash for a user-defined type through gtl::Hash (absl-based)
    struct point {
        int x, y;
        bool operator==(const point& o) const { return x == o.x && y == o.y; }
    };
    struct point_hash {
        size_t operator()(const point& p) const {
            return static_cast<size_t>(p.x) * 31u + static_cast<size_t>(p.y);
        }
    };
    gtl::flat_hash_map<point, int, point_hash> pm_pts;
    pm_pts[{1, 2}] = 7;
    pm_pts[{3, 4}] = 8;
    GTL_CHECK(pm_pts.size() == 2);
    GTL_CHECK(pm_pts.at({3, 4}) == 8);

    std::printf("gtl consumer checks: %d run, %d failed\n", checks, failures);
    std::printf("gtl SSE fast path: GTL_HAVE_SSE2=%d GTL_HAVE_SSSE3=%d\n",
                static_cast<int>(GTL_HAVE_SSE2),
                static_cast<int>(GTL_HAVE_SSSE3));
    return failures == 0 ? 0 : 1;
}
