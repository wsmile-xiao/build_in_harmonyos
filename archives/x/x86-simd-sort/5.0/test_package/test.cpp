// test_x86-simd-sort — Conan L1 consumer test (also OHOS consumer case).
//
// Simulates a real upper-layer consumer of x86-simd-sort: uses only the
// installed public header <x86simdsort.h> and the exported API
// x86simdsort::qsort / x86simdsort::argsort, verifies the observable sorted
// result matches std::sort. On aarch64 (OHOS) the library dispatches to its
// scalar implementation; on x86 to the SIMD kernels. This is a real API call
// with an observable result, not a print-only stub.
#include <x86simdsort.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <vector>

namespace {

int check_qsort()
{
    // public API: x86simdsort::qsort(T*, size_t, bool hasnan)
    const size_t n = 16384;
    std::vector<double> arr(n);
    // deterministic pseudo-random-ish data (LCG), covers random + duplicates
    uint64_t state = 0x9E3779B97F4A7C15ULL;
    for (size_t i = 0; i < n; ++i) {
        state = state * 6364136223846793005ULL + 1;
        arr[i] = static_cast<double>((state >> 33) % 100000) / 7.0;
    }
    std::vector<double> expected(arr);
    std::sort(expected.begin(), expected.end());

    x86simdsort::qsort(arr.data(), arr.size(), false);

    if (arr != expected) {
        std::fprintf(stderr, "FAIL: x86simdsort::qsort result mismatch at first "
                             "diverging element\n");
        return 1;
    }
    std::printf("x86simdsort::qsort: sorted %zu doubles OK\n", n);
    return 0;
}

int check_argsort()
{
    // public API: x86simdsort::argsort(T*, size_t, bool hasnan)
    const size_t n = 4096;
    std::vector<float> arr(n);
    uint64_t state = 0x123456789ABCDEF0ULL;
    for (size_t i = 0; i < n; ++i) {
        state = state * 6364136223846793005ULL + 1;
        arr[i] = static_cast<float>((state >> 32) % 10000) / 3.0f;
    }
    std::vector<size_t> arg = x86simdsort::argsort(arr.data(), n, false);

    if (arg.size() != n) {
        std::fprintf(stderr, "FAIL: argsort returned wrong size\n");
        return 1;
    }
    // indices must be a permutation and values must be sorted
    std::vector<bool> seen(n, false);
    for (size_t i = 0; i < n; ++i) {
        if (arg[i] >= n || seen[arg[i]]) {
            std::fprintf(stderr, "FAIL: argsort indices not a permutation\n");
            return 1;
        }
        seen[arg[i]] = true;
        if (i > 0 && arr[arg[i - 1]] > arr[arg[i]]) {
            std::fprintf(stderr, "FAIL: argsort result not sorted\n");
            return 1;
        }
    }
    std::printf("x86simdsort::argsort: %zu float indices OK\n", n);
    return 0;
}

} // namespace

int main()
{
    int rc = 0;
    rc |= check_qsort();
    rc |= check_argsort();
    if (rc == 0) {
        std::printf("test x86-simd-sort 5.0: ALL CONSUMER CHECKS PASSED\n");
    }
    return rc;
}