cmake_minimum_required(VERSION 3.15)
project(rttopo_test C CXX)

find_package(rttopo CONFIG REQUIRED)

add_executable(rttopo_test test.c)
target_link_libraries(rttopo_test rttopo::rttopo)
# geos_c (transitive dep of rttopo) is a C++ static lib → need libc++ at link
set_target_properties(rttopo_test PROPERTIES LINKER_LANGUAGE CXX)

enable_testing()
add_test(NAME rttopo_test COMMAND rttopo_test)
