cmake_minimum_required(VERSION 3.15)
project(test_libpll C)

find_package(libpll REQUIRED)

add_executable(test_libpll test.c)
target_link_libraries(test_libpll libpll::libpll)

enable_testing()
add_test(NAME test_libpll COMMAND test_libpll)
