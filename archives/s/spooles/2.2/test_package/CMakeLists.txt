cmake_minimum_required(VERSION 3.15)
project(test_spooles C)

# Find the package via Conan-generated CMakeDeps
find_package(spooles REQUIRED)

add_executable(test_spooles test_spooles.c)
target_link_libraries(test_spooles spooles::spooles)

enable_testing()
add_test(NAME test_spooles COMMAND test_spooles)
