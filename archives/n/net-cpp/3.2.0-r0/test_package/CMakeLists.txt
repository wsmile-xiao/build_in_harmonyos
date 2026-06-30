cmake_minimum_required(VERSION 3.15)
project(test_net-cpp C)

# Find the package via Conan-generated CMakeDeps
find_package(net-cpp REQUIRED)

add_executable(test_net-cpp test.c)
target_link_libraries(test_net-cpp net-cpp::net-cpp)

enable_testing()
add_test(NAME test_net-cpp COMMAND test_net-cpp)
