cmake_minimum_required(VERSION 3.15)
project(test_bird C)

add_executable(test_bird test.c)

if(BIRD_BIN_PATH)
    target_compile_definitions(test_bird PRIVATE BIRD_BIN="${BIRD_BIN_PATH}")
endif()

enable_testing()
add_test(NAME test_bird COMMAND test_bird)
