cmake_minimum_required(VERSION 3.15)
project(test_arx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(arx-libertatis REQUIRED)

add_executable(test_arx test_arx.cpp)
target_link_libraries(test_arx arx-libertatis::arx-libertatis)

enable_testing()
add_test(NAME test_arx COMMAND test_arx)
