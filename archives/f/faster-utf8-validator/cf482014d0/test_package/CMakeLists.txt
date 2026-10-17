cmake_minimum_required(VERSION 3.15)
project(test_faster-utf8-validator C)

# Find the package via Conan-generated CMakeDeps
find_package(faster-utf8-validator REQUIRED)

add_executable(test_faster-utf8-validator test.c)
target_link_libraries(test_faster-utf8-validator faster-utf8-validator::faster-utf8-validator)

enable_testing()
add_test(NAME test_faster-utf8-validator COMMAND test_faster-utf8-validator)
