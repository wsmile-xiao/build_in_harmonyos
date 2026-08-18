cmake_minimum_required(VERSION 3.15)
project(test_yaml_cpp CXX)

# Find the package via Conan-generated CMakeDeps.
find_package(yaml-cpp CONFIG REQUIRED)

enable_testing()

add_executable(test_yaml_cpp test.cpp)
target_link_libraries(test_yaml_cpp yaml-cpp::yaml-cpp)
add_test(NAME test_yaml_cpp COMMAND test_yaml_cpp)
