cmake_minimum_required(VERSION 3.15)
project(test_snmalloc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(snmalloc REQUIRED)

add_executable(test_snmalloc test_snmalloc.cpp)
target_link_libraries(test_snmalloc snmalloc::snmalloc)

enable_testing()
add_test(NAME test_snmalloc COMMAND test_snmalloc)
