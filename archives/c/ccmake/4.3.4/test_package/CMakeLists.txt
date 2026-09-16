cmake_minimum_required(VERSION 3.15)
project(test_cmake C)

# R34: exercise the packaged cmake binary through a real configure+build.
# A tiny project is generated at configure time and built at test time
# using the cmake executable found via CMakeDeps/FindCMake.
add_executable(test_cmake test.c)

# Generate the sample project consumed by the test
file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/proj")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/proj/CMakeLists.txt" [=[
cmake_minimum_required(VERSION 3.15)
project(hello C)
add_executable(hello hello.c)
]=])
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/proj/hello.c" [=[
#include <stdio.h>
int main(void) { printf("hello from packaged cmake\n"); return 0; }
]=])

enable_testing()
# Locate the packaged cmake: conan package bindir is injected via
# CMAKE_PROGRAM_PATH by the conanfiles' package_info(bindirs=["bin"]).
add_test(NAME test_cmake
         COMMAND test_cmake ${CMAKE_COMMAND}
         WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR})
