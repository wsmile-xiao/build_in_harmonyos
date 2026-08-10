cmake_minimum_required(VERSION 3.15)
project(test_pkcs11-helper C)

find_package(pkcs11-helper REQUIRED)
find_package(openssl REQUIRED)

add_executable(test_pkcs11-helper test.c)
# Link with all OpenSSL targets to ensure static libs are included
target_link_libraries(test_pkcs11-helper
    pkcs11-helper::pkcs11-helper
    OpenSSL::SSL
    OpenSSL::Crypto
    openssl::openssl
)

enable_testing()
add_test(NAME test_pkcs11-helper COMMAND test_pkcs11-helper)
