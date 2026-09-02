cmake_minimum_required(VERSION 3.15)
project(test_simpleini CXX)

# Find the package via Conan-generated CMakeDeps
find_package(simpleini REQUIRED)

add_executable(test_simpleini test.cpp)
target_link_libraries(test_simpleini simpleini::simpleini)

enable_testing()
add_test(NAME test_simpleini COMMAND test_simpleini)