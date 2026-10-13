cmake_minimum_required(VERSION 3.15)
project(test_build2 C)

# Find the package via Conan-generated CMakeDeps
find_package(build2 REQUIRED)

add_executable(test_build2 test.c)
target_link_libraries(test_build2 build2::build2)

enable_testing()
add_test(NAME test_build2 COMMAND test_build2)
