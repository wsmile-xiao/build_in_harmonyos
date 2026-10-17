cmake_minimum_required(VERSION 3.15)
project(test_g722 C)

find_package(libg722 CONFIG REQUIRED)

add_executable(test_g722 test_g722.c)
target_link_libraries(test_g722 libg722::g722)

enable_testing()
add_test(NAME test_g722 COMMAND test_g722)
