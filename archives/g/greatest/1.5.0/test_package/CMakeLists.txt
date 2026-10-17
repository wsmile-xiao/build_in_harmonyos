cmake_minimum_required(VERSION 3.15)
project(test_greatest C)

# Find the package via Conan-generated CMakeDeps
find_package(greatest REQUIRED)

add_executable(test_greatest test.c)
target_link_libraries(test_greatest greatest::greatest)

enable_testing()
add_test(NAME test_greatest COMMAND test_greatest)
