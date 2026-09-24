cmake_minimum_required(VERSION 3.15)
project(test_pbc_sig C)

find_package(pbc_sig REQUIRED)
find_package(pbc REQUIRED)

add_executable(test_pbc_sig test.c)
target_link_libraries(test_pbc_sig pbc_sig::pbc_sig pbc::pbc)

enable_testing()
add_test(NAME test_pbc_sig COMMAND test_pbc_sig)
