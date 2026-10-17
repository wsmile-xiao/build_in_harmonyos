cmake_minimum_required(VERSION 3.15)
project(test_openjpeg2 C)

find_package(openjpeg2 CONFIG REQUIRED)

add_executable(test_openjpeg2 test_openjpeg2.c)
target_link_libraries(test_openjpeg2 PRIVATE openjpeg2::openjpeg2)

enable_testing()
add_test(NAME test_openjpeg2 COMMAND test_openjpeg2)
