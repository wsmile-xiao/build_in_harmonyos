cmake_minimum_required(VERSION 3.15)
project(test_icecream-cpp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(icecream-cpp REQUIRED)

add_executable(test_icecream-cpp test_icecream.cpp)
target_link_libraries(test_icecream-cpp icecream-cpp::icecream-cpp)

enable_testing()
add_test(NAME test_icecream-cpp COMMAND test_icecream-cpp)