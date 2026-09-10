#include <cstddef>

#include <boost/multiprecision/cpp_int.hpp>

int main() {
    using FixedUint = boost::multiprecision::number<
        boost::multiprecision::cpp_int_backend<
            257,
            257,
            boost::multiprecision::unsigned_magnitude,
            boost::multiprecision::unchecked,
            void>>;

    FixedUint bits{0};
    boost::multiprecision::bit_set(bits, 0);
    boost::multiprecision::bit_set(bits, 128);
    boost::multiprecision::bit_set(bits, 256);

    int failures = 0;
    failures += !boost::multiprecision::bit_test(bits, 0);
    failures += !boost::multiprecision::bit_test(bits, 128);
    failures += !boost::multiprecision::bit_test(bits, 256);
    failures += boost::multiprecision::msb(bits) != 256;
    failures += bits.backend().size() == 0;
    failures += bits.backend().limbs()[0] == 0;

    const FixedUint joined = bits | FixedUint{2};
    failures += !boost::multiprecision::bit_test(joined, 1);
    failures += (joined & bits) != bits;
    return failures;
}
