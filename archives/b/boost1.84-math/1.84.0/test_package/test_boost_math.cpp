// test_package/test_boost_math.cpp — boost1.84-math 1.84.0 L1 smoke test.
// Exercises Boost.Math header-only APIs (constants::pi, gcd/lcm, quaternion,
// special function) plus the compiled tr1/c99 static libraries (beta/tgamma
// C-callable interface from libboost_math_tr1.a / libboost_math_c99.a).
#include <boost/math/constants/constants.hpp>
#include <boost/math/quaternion.hpp>
#include <boost/math/special_functions/gamma.hpp>
#include <boost/integer/common_factor.hpp>
#include <boost/math/tr1.hpp>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>

int main() {
    int checks = 0;

    // 1. boost::math::constants — pi<double>/pi<float>
    const double pi_d = boost::math::constants::pi<double>();
    if (std::fabs(pi_d - 3.14159265358979323846) > 1e-15) {
        std::cerr << "constants: pi<double> mismatch: " << pi_d << std::endl;
        return 1;
    }
    ++checks;
    const float pi_f = boost::math::constants::pi<float>();
    if (std::fabs(static_cast<double>(pi_f) - 3.14159265358979) > 1e-6) {
        std::cerr << "constants: pi<float> mismatch" << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "constants: pi = " << std::setprecision(17) << pi_d << std::endl;

    // 2. boost::integer gcd/lcm（math 库 common_factor 的现行入口）
    if (boost::integer::gcd(48, 18) != 6) {
        std::cerr << "integer: gcd(48,18) != 6" << std::endl;
        return 1;
    }
    ++checks;
    if (boost::integer::lcm(4, 6) != 12) {
        std::cerr << "integer: lcm(4,6) != 12" << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "integer: gcd(48,18)=" << boost::integer::gcd(48, 18)
              << " lcm(4,6)=" << boost::integer::lcm(4, 6) << " OK" << std::endl;

    // 3. boost::math::quaternion（header-only）
    boost::math::quaternion<double> q(1.0, 2.0, 3.0, 4.0);
    const double qn = std::fabs(abs(q) - std::sqrt(30.0));
    if (qn > 1e-12) {
        std::cerr << "quaternion: |1+2i+3j+4k| != sqrt(30)" << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "quaternion: |1+2i+3j+4k| = " << abs(q) << " (sqrt(30) OK)" << std::endl;

    // 4. header-only special function: tgamma<double> via boost::math namespace
    const double tg_hdr = boost::math::tgamma(5.0);
    if (std::fabs(tg_hdr - 24.0) > 1e-9) {
        std::cerr << "special_functions: tgamma(5) != 24, got " << tg_hdr << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "special_functions (header-only): tgamma(5) = " << tg_hdr << std::endl;

    // 5. compiled library: boost::math::tr1 C++ interface（链接 libboost_math_tr1）
    const double beta_v = boost::math::tr1::beta(2.0, 3.0);
    if (std::fabs(beta_v - (1.0 / 12.0)) > 1e-12) {
        std::cerr << "tr1 compiled: beta(2,3) != 1/12, got " << beta_v << std::endl;
        return 1;
    }
    ++checks;
    const double erf_v = boost::math::tr1::erf(1.0);
    if (std::fabs(erf_v - 0.84270079294971486934) > 1e-12) {
        std::cerr << "tr1 compiled: erf(1) mismatch, got " << erf_v << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "tr1 compiled: beta(2,3)=" << beta_v << " erf(1)=" << erf_v << std::endl;

    // 6. compiled library: float variant（链接 libboost_math_tr1f）
    const float betaf_v = boost::math::tr1::betaf(2.0f, 3.0f);
    if (std::fabs(static_cast<double>(betaf_v) - (1.0 / 12.0)) > 1e-6) {
        std::cerr << "tr1f compiled: betaf(2,3) mismatch, got " << betaf_v << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "tr1f compiled: betaf(2,3)=" << betaf_v << std::endl;

    // 7. compiled library: c99 interface（链接 libboost_math_c99）
    const double cbrt_v = boost::math::tr1::cbrt(27.0);
    if (std::fabs(cbrt_v - 3.0) > 1e-12) {
        std::cerr << "c99 compiled: cbrt(27) != 3, got " << cbrt_v << std::endl;
        return 1;
    }
    ++checks;
    std::cout << "c99 compiled: cbrt(27)=" << cbrt_v << std::endl;

    std::cout << "boost1.84-math 1.84.0: " << checks
              << " API checks OK (constants/gcd/lcm/quaternion/special_functions/tr1/tr1f/c99)"
              << std::endl;
    return 0;
}
