cmake_minimum_required(VERSION 3.15)
project(test_hexdump CXX)

# Find the package via Conan-generated CMakeDeps
find_package(hexdump REQUIRED)

add_executable(test_hexdump test.cpp)
target_link_libraries(test_hexdump hexdump::hexdump)
target_compile_features(test_hexdump PRIVATE cxx_std_14)

enable_testing()
add_test(NAME test_hexdump COMMAND test_hexdump)