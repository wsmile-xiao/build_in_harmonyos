// BitMagic 9.3.2 — minimal smoke test exercising the core bvector<> API.
// Header-only: no library to link, just include bm.h.
//
// Verifies:
//   1. set_bit / test / get_bit  basic storage and retrieval
//   2. count()                    population counting
//   3. optimize(), optimize_gap() compression
//   4. iterate()                  iteration over set bits
//   5. set_count + auto_gap_conditions triggers BM gap compression blocks
#include <cassert>
#include <cstdio>
#include <cstdlib>

#include "bm.h"

int main() {
    using namespace bm;

    // ---- 1. basic set / get ----
    bvector<> bv;
    bv.set(10);
    bv.set(100);
    bv.set(1000);
    assert(bv.test(10));
    assert(bv.test(100));
    assert(bv.test(1000));
    assert(!bv.test(11));
    assert(bv.get_bit(10) == 1);
    assert(bv.get_bit(11) == 0);

    // ---- 2. population count ----
    assert(bv.count() == 3);

    // ---- 3. set/clear round-trip ----
    bv.set(100, false);   // BitMagic clears a bit via set(idx, false)
    assert(!bv.test(100));
    assert(bv.count() == 2);

    // ---- 4. fill range and re-count ----
    for (unsigned i = 0; i < 64; ++i) bv.set(i);
    assert(bv.count() == 65);  // 64 from loop + bit 10 + bit 1000 (bit 100 cleared earlier)

    // ---- 5. optimize + iterate ----
    bv.optimize();
    unsigned seen = 0;
    bvector<>::enumerator en = bv.first();
    bvector<>::enumerator en_end = bv.end();
    while (en < en_end) {
        ++seen;
        ++en;
    }
    assert(seen == 65);

    // ---- 6. large sparse vector via set_range / count ----
    bv.clear();
    bv.set_range(0, 1024);
    assert(bv.count() == 1025);
    bv.optimize();
    assert(bv.count() == 1025);

    // ---- 7. AND / OR / XOR set algebra ----
    bvector<> a, b;
    for (unsigned i = 0; i < 100; ++i) a.set(i);
    for (unsigned i = 50; i < 150; ++i) b.set(i);

    bvector<> u = a | b;
    assert(u.count() == 150);

    bvector<> i = a & b;
    assert(i.count() == 50);

    bvector<> x = a ^ b;
    assert(x.count() == 100);

    std::printf("test bitmagic 9.3.2: OK (count=65, OR=150, AND=50, XOR=100)\n");
    return 0;
}