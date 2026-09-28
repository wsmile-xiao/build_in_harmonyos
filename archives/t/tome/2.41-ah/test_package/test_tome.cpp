/* Consumer test for the installed tome game engine package.
 *
 * Exercises the installed public C++ headers: flag_set<> (bit-set template
 * from src/flag_set.hpp) and grid<> (2-D template from src/grid.hpp).  Both
 * are the same utilities covered by the upstream Bandit suite, so this is a
 * genuine consumer check of the packaged headers. */
#include <cstdint>
#include <cstdio>

#include "flag_set.hpp"
#include "grid.hpp"

static int checks = 0;
static int fails = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { fails++; std::printf("FAIL: %s\n", (msg)); } \
} while (0)

int main()
{
    typedef flag_set<2> fs_t;

    CHECK(fs_t::make(0, 31)[0] == 2147483648UL, "make(0,31) sets bit 31 of tier 0");
    CHECK(fs_t::make(0, 31)[1] == 0UL, "make(0,31) leaves tier 1 empty");
    CHECK(fs_t::make(1, 31)[0] == 0UL, "make(1,31) leaves tier 0 empty");
    CHECK(fs_t::make(1, 31)[1] == 2147483648UL, "make(1,31) sets bit 31 of tier 1");
    CHECK(fs_t::make(1, 7)[1] == 128UL, "make(1,7) sets bit 7 of tier 1");

    CHECK(bool(fs_t()) == false, "empty flag_set converts to false");
    CHECK(bool(fs_t::make(1, 3)) == true, "non-empty flag_set converts to true");
    CHECK(fs_t::make(1, 3) == fs_t::make(1, 3), "equality of equal flag_sets");

    fs_t combined = fs_t::make(0, 31) | fs_t::make(1, 3);
    CHECK(combined[0] == 2147483648UL && combined[1] == 8UL, "or respects tier/index");
    fs_t masked = combined & combined;
    CHECK(masked[0] == 2147483648UL && masked[1] == 8UL, "and respects tier/index");
    CHECK(combined.count() == 2, "count() reports two set bits");

    CHECK(fs_t::make_bit(5)[0] == 32UL, "make_bit(5) sets bit 5 of tier 0");
    CHECK(fs_t::make_bit(37)[1] == 32UL, "make_bit(37) sets bit 5 of tier 1");

    grid<int> g;
    g.resize(123, 42);
    CHECK(g.width() == 123 && g.height() == 42, "grid resize sets width and height");
    g.width(7);
    CHECK(g.width() == 7 && g.height() == 42, "grid width() setter keeps height");
    g(6, 41) = 99;
    CHECK(g(6, 41) == 99, "grid operator() round-trips a value");

    std::printf("TOME_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
