cmake_minimum_required(VERSION 3.15)
project(test_libcommuni CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libcommuni REQUIRED)

add_executable(test_libcommuni test.cpp)
target_link_libraries(test_libcommuni libcommuni::libcommuni)

enable_testing()
add_test(NAME test_libcommuni COMMAND test_libcommuni)
