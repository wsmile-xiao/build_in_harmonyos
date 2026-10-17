// test_package.cpp — jwt-cpp 0.7.1 consumer test (C++)
// Verifies that a consumer can include <jwt-cpp/jwt.h> and perform a real
// HS256 sign + verify round-trip via the OpenSSL back end re-exported by
// jwt-cpp::jwt-cpp.
#include <jwt-cpp/jwt.h>
#include <iostream>
#include <string>

int main() {
    // Create a signed HS256 token
    auto token = jwt::create()
                     .set_issuer("test-consumer")
                     .set_subject("conan-test")
                     .set_issued_at(std::chrono::system_clock::now())
                     .set_expires_at(std::chrono::system_clock::now() + std::chrono::hours(1))
                     .sign(jwt::algorithm::hs256{"secret"});

    // Verify the token round-trip
    auto decoded = jwt::decode(token);
    auto verifier = jwt::verify()
                        .allow_algorithm(jwt::algorithm::hs256{"secret"})
                        .with_issuer("test-consumer");
    verifier.verify(decoded);

    if (decoded.get_subject() != "conan-test") {
        std::cerr << "FAIL: subject mismatch: " << decoded.get_subject() << std::endl;
        return 1;
    }
    std::cout << "test jwt-cpp 0.7.1: HS256 sign+verify OK" << std::endl;
    return 0;
}