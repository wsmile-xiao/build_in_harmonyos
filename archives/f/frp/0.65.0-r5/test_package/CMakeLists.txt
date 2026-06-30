cmake_minimum_required(VERSION 3.15)
project(test_frp C)

# Find the package via Conan-generated CMakeDeps
find_package(frp REQUIRED)

add_executable(test_frp test.c)
target_link_libraries(test_frp frp::frp)

enable_testing()
add_test(NAME test_frp COMMAND test_frp)
