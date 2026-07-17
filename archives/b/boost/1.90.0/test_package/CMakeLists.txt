cmake_minimum_required(VERSION 3.15)
project(test_boost CXX)

# Find the package via Conan-generated CMakeDeps
find_package(boost REQUIRED)

add_executable(test_boost test.cpp)
target_link_libraries(test_boost boost::boost)

enable_testing()
add_test(NAME test_boost COMMAND test_boost)