cmake_minimum_required(VERSION 3.15)
project(test_coinor-dylp CXX)

# Find the package via Conan-generated CMakeDeps
find_package(coinor-dylp REQUIRED)

add_executable(test_coinor-dylp test.cpp)
target_link_libraries(test_coinor-dylp coinor-dylp::coinor-dylp)

enable_testing()
add_test(NAME test_coinor-dylp COMMAND test_coinor-dylp)
