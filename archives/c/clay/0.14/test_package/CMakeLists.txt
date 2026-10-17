cmake_minimum_required(VERSION 3.15)
project(test_clay C)

find_package(clay REQUIRED)

add_executable(test_clay test_clay.c)
target_link_libraries(test_clay PRIVATE clay::clay)
set_target_properties(test_clay PROPERTIES C_STANDARD 11)
