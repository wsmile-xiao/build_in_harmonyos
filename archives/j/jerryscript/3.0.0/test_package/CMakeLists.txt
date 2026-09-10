cmake_minimum_required(VERSION 3.15)
project(test_jerryscript C)

find_package(jerryscript CONFIG REQUIRED)

add_executable(test_jerryscript test.c)
target_link_libraries(test_jerryscript PRIVATE jerryscript::jerryscript)

enable_testing()
add_test(NAME test_jerryscript COMMAND test_jerryscript)
