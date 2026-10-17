#include <pbc/pbc.h>
#include <pbc/pbcxx.h>

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

constexpr char kTypeAParams[] =
    "type a\n"
    "q 8780710799663312522437781984754049815806883199414208211028653399266475630880222957078625179422662221423155858769582317459277713367317481324925129998224791\n"
    "h 12016012264891146079388821366740534204802954401251311822919615131047207289359704531102844802183906537786776\n"
    "r 730750818665451621361119245571504901405976559617\n"
    "exp2 159\n"
    "exp1 107\n"
    "sign1 1\n"
    "sign0 1\n";

int failures = 0;

void check(bool condition, const char* description) {
    if (condition) {
        std::cout << "  ok   " << description << '\n';
    } else {
        std::cerr << "  FAIL " << description << '\n';
        ++failures;
    }
}

void test_c_api() {
    pairing_t pairing;
    element_t exponent;
    element_t g1;
    element_t g1_power;
    element_t g1_roundtrip;
    element_t g2;
    element_t g2_power;
    element_t base_pairing;
    element_t expected_pairing;
    element_t actual_pairing;

    check(pairing_init_set_buf(pairing, kTypeAParams, sizeof(kTypeAParams) - 1) == 0,
          "C API parses Type A parameters");
    check(pairing_is_symmetric(pairing) != 0, "Type A pairing is symmetric");

    element_init_Zr(exponent, pairing);
    element_init_G1(g1, pairing);
    element_init_G1(g1_power, pairing);
    element_init_G1(g1_roundtrip, pairing);
    element_init_G2(g2, pairing);
    element_init_G2(g2_power, pairing);
    element_init_GT(base_pairing, pairing);
    element_init_GT(expected_pairing, pairing);
    element_init_GT(actual_pairing, pairing);

    element_from_hash(g1, const_cast<char*>("consumer-g1"), 11);
    element_from_hash(g2, const_cast<char*>("consumer-g2"), 11);
    element_set_si(exponent, 37);
    check(element_is0(g1) == 0, "G1 hash maps to a nonzero element");
    check(element_is0(g2) == 0, "G2 hash maps to a nonzero element");

    pairing_apply(base_pairing, g1, g2, pairing);
    element_pow_zn(expected_pairing, base_pairing, exponent);
    element_pow_zn(g1_power, g1, exponent);
    pairing_apply(actual_pairing, g1_power, g2, pairing);
    check(element_cmp(expected_pairing, actual_pairing) == 0,
          "e(g1^a, g2) equals e(g1, g2)^a");

    element_pow_zn(g2_power, g2, exponent);
    pairing_apply(actual_pairing, g1, g2_power, pairing);
    check(element_cmp(expected_pairing, actual_pairing) == 0,
          "e(g1, g2^a) equals e(g1, g2)^a");

    const int byte_count = element_length_in_bytes(g1);
    check(byte_count > 0, "G1 serialized size is positive");
    auto* bytes = static_cast<unsigned char*>(std::malloc(static_cast<std::size_t>(byte_count)));
    check(bytes != nullptr, "serialization buffer allocation succeeds");
    if (bytes) {
        check(element_to_bytes(bytes, g1) == byte_count,
              "G1 serialization writes the advertised size");
        check(element_from_bytes(g1_roundtrip, bytes) == byte_count,
              "G1 deserialization consumes the complete buffer");
        check(element_cmp(g1, g1_roundtrip) == 0, "G1 serialization round-trip preserves value");
        std::free(bytes);
    }

    element_clear(actual_pairing);
    element_clear(expected_pairing);
    element_clear(base_pairing);
    element_clear(g2_power);
    element_clear(g2);
    element_clear(g1_roundtrip);
    element_clear(g1_power);
    element_clear(g1);
    element_clear(exponent);
    pairing_clear(pairing);
}

void test_cpp_api() {
    pbc::Pairing pairing(kTypeAParams);
    check(pairing.is_symmetric(), "C++ Pairing reports Type A symmetry");

    pbc::ZrElement left(pairing);
    pbc::ZrElement right(pairing);
    pbc::ZrElement expected(pairing);
    left.set_si(17);
    right.set_si(25);
    expected.set_si(42);
    check(left + right == expected, "C++ Zr addition returns 42");

    pbc::G1Element g1(pairing);
    pbc::G2Element g2(pairing);
    pbc::ZrElement exponent(pairing);
    g1.from_hash("cpp-consumer-g1");
    g2.from_hash("cpp-consumer-g2");
    exponent.set_si(19);
    check(pairing(g1 * exponent, g2) == pairing(g1, g2 * exponent),
          "C++ wrapper preserves pairing bilinearity");

    const std::string serialized = g1.to_bytes();
    pbc::G1Element restored(pairing);
    check(!serialized.empty(), "C++ wrapper serializes a G1 element");
    check(restored.from_bytes(serialized) == g1,
          "C++ wrapper deserializes the original G1 element");
}

}  // namespace

int main() {
    pbc_random_set_deterministic(20260909);
    test_c_api();
    test_cpp_api();
    std::cout << "PBC consumer assertions: " << (16 - failures) << "/16 passed\n";
    return failures == 0 ? 0 : 1;
}
