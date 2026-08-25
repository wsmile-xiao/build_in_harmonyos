cmake_minimum_required(VERSION 3.15)
project(test_libdivide CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libdivide REQUIRED)

add_executable(test_libdivide test.cpp)
target_link_libraries(test_libdivide libdivide::libdivide)

enable_testing()
add_test(NAME test_libdivide COMMAND test_libdivide)
