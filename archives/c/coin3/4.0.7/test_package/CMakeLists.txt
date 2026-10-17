cmake_minimum_required(VERSION 3.15)
project(test_coin3 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coin3 REQUIRED)

add_executable(test_coin3 test.cpp)
target_link_libraries(test_coin3 coin3::coin3)

enable_testing()
add_test(NAME test_coin3 COMMAND test_coin3)
