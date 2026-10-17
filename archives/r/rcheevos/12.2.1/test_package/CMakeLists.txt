cmake_minimum_required(VERSION 3.15)
project(test_rcheevos C)

find_package(rcheevos REQUIRED)

add_executable(test_rcheevos test.c)
target_link_libraries(test_rcheevos PRIVATE rcheevos::rcheevos)

enable_testing()
add_test(NAME test_rcheevos COMMAND test_rcheevos)
