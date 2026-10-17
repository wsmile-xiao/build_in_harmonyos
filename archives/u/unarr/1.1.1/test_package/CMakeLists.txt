cmake_minimum_required(VERSION 3.15)
project(test_unarr C)

find_package(unarr REQUIRED)

add_executable(test_unarr test.c)
target_link_libraries(test_unarr PRIVATE unarr::unarr)

enable_testing()
add_test(NAME test_unarr COMMAND test_unarr)
