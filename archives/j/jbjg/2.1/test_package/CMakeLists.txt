cmake_minimum_required(VERSION 3.15)
project(test_jbjg C)

find_package(JBIG REQUIRED)

add_executable(test_jbjg test.c)
target_link_libraries(test_jbjg JBIG::JBIG)

enable_testing()
add_test(NAME test_jbjg COMMAND test_jbjg)
