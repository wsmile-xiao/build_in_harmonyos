cmake_minimum_required(VERSION 3.15)
project(test_kbd C)

add_executable(test_kbd test.c)
target_compile_definitions(test_kbd PRIVATE KBD_BIN_DIR="${KBD_BIN_DIR}")

enable_testing()
add_test(NAME test_kbd COMMAND test_kbd)
