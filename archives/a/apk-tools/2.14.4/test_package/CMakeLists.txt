cmake_minimum_required(VERSION 3.15)
project(test_apk C)

# Find the package via Conan-generated CMakeDeps
find_package(apk-tools REQUIRED)
find_package(openssl REQUIRED)
find_package(zlib REQUIRED)

add_executable(test_apk test.c)
target_link_libraries(test_apk apk-tools::apk-tools openssl::openssl ZLIB::ZLIB)

enable_testing()
add_test(NAME test_apk COMMAND test_apk)
