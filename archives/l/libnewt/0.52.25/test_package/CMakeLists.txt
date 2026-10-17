cmake_minimum_required(VERSION 3.15)
project(test_newt C)

# Find the package via Conan-generated CMakeDeps
find_package(libnewt REQUIRED)

add_executable(test_newt test_newt.c)
target_link_libraries(test_newt PRIVATE libnewt::libnewt)

enable_testing()
add_test(NAME test_newt COMMAND test_newt)
