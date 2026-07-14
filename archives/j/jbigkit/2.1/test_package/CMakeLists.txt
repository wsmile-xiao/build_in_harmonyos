cmake_minimum_required(VERSION 3.15)
project(test_jbigkit C)

find_package(JBIG REQUIRED)

add_executable(test_jbig test.c)
target_link_libraries(test_jbig JBIG::JBIG)

enable_testing()
add_test(NAME test_jbig COMMAND test_jbig)
