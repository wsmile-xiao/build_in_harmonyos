cmake_minimum_required(VERSION 3.15)
project(test_cpp_ipc CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cpp-ipc REQUIRED)

add_executable(test_cpp_ipc test.cpp)
target_link_libraries(test_cpp_ipc cpp-ipc::cpp-ipc)

enable_testing()
add_test(NAME test_cpp_ipc COMMAND test_cpp_ipc)
