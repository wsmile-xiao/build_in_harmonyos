// test_tl-function-ref.cpp — Conan L1 consumer test.
// Actually invokes tl::function_ref (non-owning callable reference) to prove
// the packaged header + CMake target are consumable on OHOS/aarch64.
//
// NOTE: function_ref is a *non-owning* reference: it stores only the address
// of the callable. The callable must therefore outlive the function_ref.
// We keep every callable object as a named local so lifetime is safe.
#include <tl/function_ref.hpp>

#include <cstdio>
#include <vector>

namespace {

// Plain free function as a call target (static storage: always valid).
int add_one(int x) { return x + 1; }

struct Multiplier {
    int factor;
    int apply(int x) const { return x * factor; }
};

// Generic algorithm that consumes the packaged header.
int sum(std::vector<int> const& values, tl::function_ref<int(int)> fn) {
    int acc = 0;
    for (auto const& v : values) {
        acc += fn(v);
    }
    return acc;
}

}  // namespace

int main() {
    int failures = 0;

    // 1) Free function target.
    tl::function_ref<int(int)> f = add_one;
    if (f(41) != 42) {
        std::printf("FAIL: free function target\n");
        ++failures;
    }

    // 2) Stateless lambda target (named local, outlives the reference).
    auto times_two = [](int v) { return v * 2; };
    tl::function_ref<int(int)> l = times_two;
    if (l(21) != 42) {
        std::printf("FAIL: stateless lambda target\n");
        ++failures;
    }

    // 3) Stateful member call target via a named capture lambda.
    Multiplier m{3};
    auto apply_m = [&m](int v) { return m.apply(v); };
    tl::function_ref<int(int)> mem = apply_m;
    if (mem(14) != 42) {
        std::printf("FAIL: stateful member target\n");
        ++failures;
    }

    // 4) Generic algorithm consuming function_ref.
    std::vector<int> vals{1, 2, 3, 4};
    if (sum(vals, add_one) != 14) {  // 2+3+4+5
        std::printf("FAIL: generic sum\n");
        ++failures;
    }

    if (failures == 0) {
        std::printf("test_tl-function-ref: OK (4 checks)\n");
        return 0;
    }
    std::printf("test_tl-function-ref: %d FAILURE(S)\n", failures);
    return 1;
}