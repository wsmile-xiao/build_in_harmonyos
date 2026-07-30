cmake_minimum_required(VERSION 3.15)
project(test_mpfr C)

find_package(mpfr REQUIRED)
find_package(gmp REQUIRED)

add_executable(test_mpfr test.c)
target_include_directories(
    test_mpfr PRIVATE
    $<TARGET_PROPERTY:gmp::gmp,INTERFACE_INCLUDE_DIRECTORIES>
)
target_link_libraries(test_mpfr PRIVATE gmp::gmp mpfr::mpfr)

enable_testing()
add_test(NAME test_mpfr COMMAND test_mpfr)
