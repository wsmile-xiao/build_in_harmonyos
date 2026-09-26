cmake_minimum_required(VERSION 3.15)
project(test_cn-cbor C)

# Find the package via Conan-generated CMakeDeps
find_package(cn-cbor REQUIRED)

add_executable(test_cn-cbor test.c)
target_link_libraries(test_cn-cbor cn-cbor::cn-cbor)

enable_testing()
add_test(NAME test_cn-cbor COMMAND test_cn-cbor)
