cmake_minimum_required(VERSION 3.15)
project(test_zpp_bits CXX)

# Find the package via Conan-generated CMakeDeps
find_package(zpp_bits REQUIRED)

add_executable(test_zpp_bits test.cpp)
target_link_libraries(test_zpp_bits PRIVATE zpp_bits::zpp_bits)
set_property(TARGET test_zpp_bits PROPERTY CXX_STANDARD 20)
set_property(TARGET test_zpp_bits PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_zpp_bits COMMAND test_zpp_bits)
