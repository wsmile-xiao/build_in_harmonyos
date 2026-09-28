cmake_minimum_required(VERSION 3.15)
project(test_librepfunc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(librepfunc REQUIRED)

add_executable(test_librepfunc test.cpp)
target_link_libraries(test_librepfunc librepfunc::librepfunc)

enable_testing()
add_test(NAME test_librepfunc COMMAND test_librepfunc)