cmake_minimum_required(VERSION 3.15)
project(test_ixwebsocket CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ixwebsocket REQUIRED)

add_executable(test_ixwebsocket test.cpp)
target_link_libraries(test_ixwebsocket ixwebsocket::ixwebsocket)

enable_testing()
add_test(NAME test_ixwebsocket COMMAND test_ixwebsocket)
