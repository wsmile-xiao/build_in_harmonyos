// Consumer verification for mpreal/3.7.1 (R34).
// Compiles against the installed <mpreal.h>, links mpfr+gmp from the
// dependency graph, asserts real computed values, and must execute.
#include <mpreal.h>

#include <cassert>
#include <iostream>
#include <string>

int main() {
    mpfr::mpreal::set_default_prec(256);
    assert(mpfr::mpreal::get_default_prec() == 256);

    const mpfr::mpreal a("1.5");
    const mpfr::mpreal b("2.25");
    const mpfr::mpreal c = a * b;  // 3.375, exactly representable
    assert(c == mpfr::mpreal("3.375"));
    assert(c.toDouble() > 3.3749999 && c.toDouble() < 3.3750001);

    const mpfr::mpreal s = mpfr::sqrt(mpfr::mpreal("2"));
    assert(s > mpfr::mpreal("1.4") && s < mpfr::mpreal("1.5"));
    const mpfr::mpreal sq = s * s;
    assert(sq > mpfr::mpreal("1.999999999999999999999999"));
    assert(sq < mpfr::mpreal("2.000000000000000000000001"));

    const std::string repr = s.toString(20, 10);
    assert(!repr.empty());
    assert(repr.find("1.41421356237309504") == 0);

    assert(mpfr::mpreal("0.5") < a);
    assert(!(mpfr::mpreal("-1") > mpfr::mpreal("0")));

    std::cout << "mpreal consumer test OK: sqrt(2) ~= " << repr << std::endl;
    return 0;
}
