cmake_minimum_required(VERSION 3.15)
project(test_ino LANGUAGES C CXX)

find_package(ino-headers REQUIRED)

add_executable(test_ino_cpp test_ino.cpp)
target_link_libraries(test_ino_cpp ino-headers::ino-headers)
set_target_properties(test_ino_cpp PROPERTIES CXX_STANDARD 11 CXX_STANDARD_REQUIRED ON)

add_executable(test_ino_c test_ino_c.c)
target_link_libraries(test_ino_c ino-headers::ino-headers)
set_target_properties(test_ino_c PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_ino_cpp COMMAND test_ino_cpp)
add_test(NAME test_ino_c COMMAND test_ino_c)
