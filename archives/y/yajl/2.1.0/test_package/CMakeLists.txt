cmake_minimum_required(VERSION 3.15)
project(test_yajl C)

# Find the package via Conan-generated CMakeDeps
find_package(yajl REQUIRED)

add_executable(test_yajl test.c)
target_link_libraries(test_yajl yajl::yajl)

enable_testing()
add_test(NAME test_yajl COMMAND test_yajl)
