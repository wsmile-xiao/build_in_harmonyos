#include <nanobench.h>

#include <cstdint>

int main() {
    ankerl::nanobench::Rng first(123);
    ankerl::nanobench::Rng second(123);
    if (first() != second()) {
        return 1;
    }

    uint64_t value = 0;
    ankerl::nanobench::Bench bench;
    bench.output(nullptr).epochs(1).epochIterations(1).run("consumer smoke", [&] { ++value; });
    return value > 0 ? 0 : 2;
}
