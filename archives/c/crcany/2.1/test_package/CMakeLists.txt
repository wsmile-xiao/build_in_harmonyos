cmake_minimum_required(VERSION 3.15)
project(test_crcany LANGUAGES C)

find_package(crcany REQUIRED CONFIG)

add_executable(test_crcany test.c)
target_link_libraries(test_crcany PRIVATE crcany::crcany)

enable_testing()
add_test(NAME test_crcany COMMAND test_crcany)
