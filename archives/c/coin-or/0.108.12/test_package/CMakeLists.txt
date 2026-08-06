cmake_minimum_required(VERSION 3.15)
project(test_coin-or CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coin-or REQUIRED)

add_executable(test_coin-or test.cpp)
target_link_libraries(test_coin-or coin-or::coin-or)

enable_testing()
add_test(NAME test_coin-or COMMAND test_coin-or)
