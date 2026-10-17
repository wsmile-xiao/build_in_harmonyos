cmake_minimum_required(VERSION 3.15)
project(test_protobuf-c C)

# Find the package via Conan-generated CMakeDeps
find_package(protobuf-c REQUIRED)

add_executable(test_protobuf-c test.c)
target_link_libraries(test_protobuf-c protobuf-c::protobuf-c)

enable_testing()
add_test(NAME test_protobuf-c COMMAND test_protobuf-c)
