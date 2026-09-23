// test_package consumer test for bbhash 1.0.0 (header-only library).
//
// This is a REAL consumer test (R34): it includes only the public header
// BooPHF.h shipped by the package, builds a minimal perfect hash function
// over N public-key integers and verifies every lookup returns a unique
// index in [0, N) — exactly the correctness property the upstream
// Bootest -check path asserts (check_mphf_correctness).
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>

#include "BooPHF.h"

int main() {
    typedef boomphf::SingleHashFunctor<uint64_t> hasher_t;
    typedef boomphf::mphf<uint64_t, hasher_t> boophf_t;

    const uint64_t N = 100000;
    std::vector<uint64_t> keys;
    keys.reserve(N);
    // Deterministic pseudo-random key set (no duplicates).
    uint64_t x = 0x9E3779B97F4A7C15ULL;
    for (uint64_t i = 0; i < N; ++i) {
        x ^= x << 13; x ^= x >> 7; x ^= x << 17;
        keys.push_back(x);
    }

    int nthreads = 2;
    boophf_t* bphf = new boophf_t(keys.size(), keys, nthreads);
    assert(bphf);

    std::vector<bool> seen(N, false);
    for (uint64_t i = 0; i < keys.size(); ++i) {
        uint64_t idx = bphf->lookup(keys[i]);
        if (idx >= N || seen[idx]) {
            printf("FAIL: lookup(%llu) = %llu (out of range or duplicate)\n",
                   (unsigned long long)keys[i], (unsigned long long)idx);
            delete bphf;
            return 1;
        }
        seen[idx] = true;
    }
    delete bphf;
    printf("bbhash consumer test PASSED: %llu keys built + %llu lookups verified\n",
           (unsigned long long)N, (unsigned long long)N);
    return 0;
}