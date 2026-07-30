cmake_minimum_required(VERSION 3.16)
project(test_libressl C)

find_package(LibreSSL CONFIG REQUIRED)

add_executable(test_libressl test_libressl.c)
target_link_libraries(
    test_libressl
    PRIVATE
        LibreSSL::TLS
        LibreSSL::SSL
        LibreSSL::Crypto
)
