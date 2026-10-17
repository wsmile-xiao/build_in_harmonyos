cmake_minimum_required(VERSION 3.15)
project(test_bifrost CXX)

# Find the package via Conan-generated CMakeDeps
find_package(bifrost REQUIRED)

add_executable(test_bifrost test.cpp)
target_link_libraries(test_bifrost bifrost::bifrost)

enable_testing()
add_test(NAME test_bifrost COMMAND test_bifrost)
