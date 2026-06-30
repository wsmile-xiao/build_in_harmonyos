cmake_minimum_required(VERSION 3.15)
project(test_drafter C)

# Find the package via Conan-generated CMakeDeps
find_package(drafter REQUIRED)

add_executable(test_drafter test.c)
target_link_libraries(test_drafter drafter::drafter)

enable_testing()
add_test(NAME test_drafter COMMAND test_drafter)
