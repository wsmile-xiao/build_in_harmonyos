cmake_minimum_required(VERSION 3.15)
project(test_coinor_ipopt CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coinor-ipopt REQUIRED)

add_executable(test_coinor_ipopt test.cpp)
target_link_libraries(test_coinor_ipopt coinor-ipopt::coinor-ipopt)

enable_testing()
add_test(NAME test_coinor_ipopt COMMAND test_coinor_ipopt)
