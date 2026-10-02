cmake_minimum_required(VERSION 3.15)
project(test_yate CXX)

# Find the package via Conan-generated CMakeDeps
find_package(yate REQUIRED)

add_executable(test_yate test.cpp)
target_link_libraries(test_yate PRIVATE yate::yate)

enable_testing()
add_test(NAME test_yate COMMAND test_yate)
