cmake_minimum_required(VERSION 3.16)
project(test_libslz LANGUAGES C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

find_package(libslz REQUIRED)

add_executable(test_slz test.c)
target_link_libraries(test_slz PRIVATE libslz::libslz)

enable_testing()
add_test(NAME test_slz COMMAND test_slz)
