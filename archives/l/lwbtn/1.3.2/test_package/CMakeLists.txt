cmake_minimum_required(VERSION 3.15)
project(test_lwbtn C)

# Find the package via Conan-generated CMakeDeps
find_package(lwbtn REQUIRED)

add_executable(test_lwbtn test.c)
target_link_libraries(test_lwbtn lwbtn::lwbtn)

enable_testing()
add_test(NAME test_lwbtn COMMAND test_lwbtn)
