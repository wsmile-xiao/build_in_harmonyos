cmake_minimum_required(VERSION 3.15)
project(sirocco_test LANGUAGES CXX)

# Find the package via Conan-generated CMakeDeps.
# sirocco::sirocco's cpp_info.requires pulls in gmp::gmp / mpfr::mpfr,
# so mpfr headers (included by sirocco.h) and gmp/mpfr libs link transitively.
find_package(sirocco CONFIG REQUIRED)

add_executable(test_sirocco test_sirocco.cpp)
target_link_libraries(test_sirocco PRIVATE sirocco::sirocco)

enable_testing()
add_test(NAME test_sirocco COMMAND test_sirocco)
