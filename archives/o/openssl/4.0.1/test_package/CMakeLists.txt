cmake_minimum_required(VERSION 3.15)
project(test_openssl C)

set(CMAKE_SKIP_RPATH ON)

find_package(OpenSSL REQUIRED CONFIG)

add_executable(test_openssl test_openssl.c)
target_link_libraries(test_openssl PRIVATE OpenSSL::SSL OpenSSL::Crypto)
