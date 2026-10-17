cmake_minimum_required(VERSION 3.15)
project(test_xvidcore C)

find_package(xvidcore REQUIRED)

add_executable(test_xvidcore test_xvidcore.c)
target_link_libraries(test_xvidcore xvidcore::xvidcore)

enable_testing()
add_test(NAME test_xvidcore COMMAND test_xvidcore)
