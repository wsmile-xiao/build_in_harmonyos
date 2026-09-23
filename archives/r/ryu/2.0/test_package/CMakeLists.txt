cmake_minimum_required(VERSION 3.15)
project(test_ryu C)

# Find the package via Conan-generated CMakeDeps
find_package(ryu REQUIRED)

add_executable(test_ryu test.c)
target_link_libraries(test_ryu ryu::ryu)

enable_testing()
add_test(NAME test_ryu COMMAND test_ryu)
