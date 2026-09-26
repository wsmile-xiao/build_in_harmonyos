cmake_minimum_required(VERSION 3.15)
project(test_libuev C)

# Find the package via Conan-generated CMakeDeps
find_package(libuev REQUIRED)

add_executable(test_libuev test.c)
target_link_libraries(test_libuev libuev::libuev)

enable_testing()
add_test(NAME test_libuev COMMAND test_libuev)
