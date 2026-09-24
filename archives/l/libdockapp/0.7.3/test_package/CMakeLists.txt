cmake_minimum_required(VERSION 3.20)
project(libdockapp_test_package C)

set(CMAKE_C_EXTENSIONS ON)

find_package(libdockapp CONFIG REQUIRED)

add_executable(libdockapp_test test.c)
target_link_libraries(libdockapp_test PRIVATE libdockapp::libdockapp)
target_compile_options(libdockapp_test PRIVATE -Wall -Wextra -Werror)
