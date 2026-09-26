cmake_minimum_required(VERSION 3.15)
project(test_cppp-reiconv C)

# Find the package via Conan-generated CMakeDeps
find_package(cppp-reiconv REQUIRED)

add_executable(test_cppp-reiconv test.c)
target_link_libraries(test_cppp-reiconv cppp-reiconv::cppp-reiconv)

enable_testing()
add_test(NAME test_cppp-reiconv COMMAND test_cppp-reiconv)
