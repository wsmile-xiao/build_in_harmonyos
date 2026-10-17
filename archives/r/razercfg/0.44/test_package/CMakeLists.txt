cmake_minimum_required(VERSION 3.15)
project(test_razercfg C)

find_package(razercfg REQUIRED)

add_executable(test_razercfg test.c)
target_link_libraries(test_razercfg razercfg::razercfg)

enable_testing()
add_test(NAME test_razercfg COMMAND test_razercfg)
