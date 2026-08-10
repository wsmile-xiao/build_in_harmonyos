cmake_minimum_required(VERSION 3.15)
project(librttopo_test C CXX)

find_package(rttopo CONFIG REQUIRED)

add_executable(test_librttopo test.c)
target_link_libraries(test_librttopo PRIVATE rttopo::rttopo)
set_target_properties(test_librttopo PROPERTIES LINKER_LANGUAGE CXX)
