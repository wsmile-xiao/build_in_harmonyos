// test_package.cpp — cpp-jwt 1.5.1 consumer test.
// Exercises the real public API: HS256 encode -> decode round-trip plus
// claim helpers. Returns non-zero on any mismatch.
#include <cassert>
#include <iostream>
#include <string>

#include "jwt/jwt.hpp"

int main() {
    using namespace jwt::params;

    const std::string key = "harmonyos-test-secret";

    // 1) Encode with a string payload claim.
    jwt::jwt_object obj{algorithm("HS256"), payload({{"some", "payload"}}),
                        secret(key)};
    std::error_code ec;
    std::string enc = obj.signature(ec);
    if (ec) {
        std::cerr << "FAIL: signature error: " << ec.message() << std::endl;
        return 1;
    }
    if (enc.empty()) {
        std::cerr << "FAIL: empty token" << std::endl;
        return 1;
    }

    // 2) Decode and verify header/payload contents.
    auto dec = jwt::decode(enc, algorithms({"HS256"}), ec, secret(key));
    if (ec) {
        std::cerr << "FAIL: decode error: " << ec.message() << std::endl;
        return 1;
    }
    if (!dec.has_claim("some")) {
        std::cerr << "FAIL: payload claim missing" << std::endl;
        return 1;
    }
    if (!dec.payload().has_claim_with_value("some", "payload")) {
        std::cerr << "FAIL: payload claim value mismatch" << std::endl;
        return 1;
    }
    if (dec.header().algo() != jwt::algorithm::HS256) {
        std::cerr << "FAIL: algorithm mismatch" << std::endl;
        return 1;
    }

    // 3) Wrong key must fail verification.
    auto bad = jwt::decode(enc, algorithms({"HS256"}), ec, secret("wrong-key"),
                           verify(true));
    (void)bad;
    if (!ec) {
        std::cerr << "FAIL: wrong key unexpectedly verified" << std::endl;
        return 1;
    }

    std::cout << "test cpp-jwt 1.5.1: HS256 sign+verify OK" << std::endl;
    return 0;
}
