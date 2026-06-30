cmake_minimum_required(VERSION 3.15)
project(test_ixwebsocket-libs C)

# Find the package via Conan-generated CMakeDeps
find_package(ixwebsocket-libs REQUIRED)

add_executable(test_ixwebsocket-libs test.c)
target_link_libraries(test_ixwebsocket-libs ixwebsocket-libs::ixwebsocket-libs)

enable_testing()
add_test(NAME test_ixwebsocket-libs COMMAND test_ixwebsocket-libs)
