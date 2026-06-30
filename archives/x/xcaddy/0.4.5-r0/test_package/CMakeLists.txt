cmake_minimum_required(VERSION 3.15)
project(test_xcaddy C)

# Find the package via Conan-generated CMakeDeps
find_package(xcaddy REQUIRED)

add_executable(test_xcaddy test.c)
target_link_libraries(test_xcaddy xcaddy::xcaddy)

enable_testing()
add_test(NAME test_xcaddy COMMAND test_xcaddy)
