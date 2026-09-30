/*
 * test_medianfilter_cpp.cpp — consumer of the public C++ header-only
 * template.  Uses only the installed public header MedianFilter.hpp.
 */
#include <MedianFilter.hpp>
#include <cstdio>

int main()
{
    MedianFilter<int, 5> filter; /* window size 5, odd >= 3 */
    int in[5] = {1, 2, 3, 4, 5};
    int got = 0;
    for (int i = 0; i < 5; i++) {
        got = filter.Insert(in[i]);
    }
    int expected = 3; /* median of 1..5 = 3 */
    if (got != expected) {
        std::fprintf(stderr, "FAIL: got=%d expected=%d\n", got, expected);
        return 1;
    }
    std::printf("PASS: C++ template median=%d\n", got);
    return 0;
}
