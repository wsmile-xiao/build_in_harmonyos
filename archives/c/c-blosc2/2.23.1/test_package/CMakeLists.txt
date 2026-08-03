cmake_minimum_required(VERSION 3.15)
project(test_c_blosc2 C)

find_package(Blosc2 REQUIRED)

add_executable(test_c_blosc2 test_c_blosc2.c)
target_link_libraries(test_c_blosc2 Blosc2::blosc2)

enable_testing()
add_test(NAME test_c_blosc2 COMMAND test_c_blosc2)
