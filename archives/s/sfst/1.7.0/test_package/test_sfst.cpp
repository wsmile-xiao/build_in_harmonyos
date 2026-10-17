// test_sfst.cpp -- consumer test for sfst/1.7.0 (calls real libsfst API).
//
// Verifies the installed libsfst can be linked and used:
//  1. SFST::Alphabet symbol round-trip (add_symbol/symbol2code/code2symbol).
//  2. SFST::Label epsilon semantics (Label::epsilon handling).
// Both exercise real library code; a stub returning 0 would not link.
#include <cassert>
#include <cstdio>
#include <string>

#include "alphabet.h"

int main() {
    // Test 1: Alphabet symbol round-trip.
    SFST::Alphabet alpha;
    SFST::Character code = alpha.add_symbol("a");
    int looked_up = alpha.symbol2code("a");
    assert(looked_up != EOF);
    assert(looked_up == (int)code);
    std::string back = alpha.code2symbol(code);
    assert(back == "a");
    std::printf("alphabet round-trip ok: code=%u symbol=%s\n",
                (unsigned)code, back.c_str());

    // Test 2: epsilon label is recognised as epsilon.
    SFST::Label eps;
    assert(eps.is_epsilon() != 0);
    SFST::Label pair((SFST::Character)code, (SFST::Character)code);
    assert(pair.is_epsilon() == 0);
    assert(pair.upper_char() == code);
    assert(pair.lower_char() == code);
    std::printf("label epsilon semantics ok\n");

    std::printf("SFST_CONSUMER_TEST_PASSED count=2/2\n");
    return 0;
}
