// test_package/test.cpp — R34: substantive agg API test
// Exercises agg::pod_array<int> (core container, no platform deps),
// verifying libagg headers link correctly. C++ required (agg is template-only).
#include <agg2/agg_array.h>

#include <cassert>
#include <cstdio>

int main(void) {
    typedef agg::pod_array<int> IntArray;
    IntArray a(3);
    a[0] = 10;
    a[1] = 20;
    a[2] = 30;
    int sum = a[0] + a[1] + a[2];
    // Sanity: pod_array behaves as a plain POD container.
    assert(sum == 60);
    assert(a.size() == 3);
    printf("agg::pod_array<int> test OK: size=%u sum=%d\n",
           static_cast<unsigned>(a.size()), sum);
    return 0;
}
