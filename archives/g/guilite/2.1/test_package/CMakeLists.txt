cmake_minimum_required(VERSION 3.15)
project(test_guilite CXX)

# Find the package via Conan-generated CMakeDeps
find_package(guilite REQUIRED)

add_executable(test_guilite test.cpp)
target_link_libraries(test_guilite guilite::guilite)

enable_testing()
add_test(NAME test_guilite COMMAND test_guilite)
