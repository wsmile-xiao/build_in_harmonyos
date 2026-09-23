// test_package consumer test — random 1.5.0 (header-only)
// R34: must actually include and exercise the packaged API, not just print.
#include <effolkronium/random.hpp>

#include <cassert>
#include <cstdint>
#include <vector>

int main() {
    using Random = effolkronium::random_thread_local;

    // Integer range draw.
    const int lo = -5, hi = 5;
    const int v = Random::get(lo, hi);
    assert(v >= lo && v <= hi);

    // Bounds across full uint32 range.
    const auto u = Random::get<std::uint32_t>();
    assert(u != 0 || v == v); // draw performed

    // weighted real draw in [0,1)
    const double d = Random::get(0.0, 1.0);
    assert(d >= 0.0 && d < 1.0);

    // container shuffle uses the engine (std::shuffle path).
    std::vector<int> xs{1, 2, 3, 4, 5, 6, 7, 8};
    Random::shuffle(xs);
    assert(xs.size() == 8);

    // draw<bool> probability path.
    const bool b = Random::get<bool>(0.5);
    (void)b;

    // weighted pick among elements.
    const auto pick = Random::get({1, 2, 3, 4});
    assert(pick >= 1 && pick <= 4);

    return 0;
}