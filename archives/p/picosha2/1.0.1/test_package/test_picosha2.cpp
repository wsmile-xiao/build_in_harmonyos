// test_picosha2.cpp — picosha2 header-only consumer test (R34)
// Actually includes picosha2.h and verifies known SHA-256 test vectors.
#include <picosha2.h>

#include <iostream>
#include <string>

static int failures = 0;

static void check_hex(const std::string &input, const std::string &expect)
{
    std::string got = picosha2::hash256_hex_string(input);
    if (got != expect) {
        std::cerr << "FAIL: hash256_hex_string(\"" << input << "\")\n"
                  << "  expected: " << expect << "\n"
                  << "  got:      " << got << std::endl;
        ++failures;
    } else {
        std::cout << "ok: " << input << std::endl;
    }
}

int main()
{
    // NIST / RFC 6234 test vectors
    check_hex("", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
    check_hex("abc", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    check_hex("The quick brown fox jumps over the lazy dog",
              "d7a8fbb307d7809469ca9abcb0082e4f8d5651e46d3cdb762d02d0bf37c9e592");
    check_hex("abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq",
              "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1");

    if (failures > 0) {
        std::cerr << failures << " assertion(s) failed" << std::endl;
        return 1;
    }
    std::cout << "all picosha2 consumer assertions passed" << std::endl;
    return 0;
}
