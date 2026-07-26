cmake_minimum_required(VERSION 3.15)
project(test_neko C)

find_package(neko CONFIG REQUIRED)

add_executable(test_neko test.c)

target_link_libraries(
    test_neko
    PRIVATE
    neko::neko
)

enable_testing()
add_test(NAME test_neko COMMAND test_neko)
