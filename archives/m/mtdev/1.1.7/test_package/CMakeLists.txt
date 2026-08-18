cmake_minimum_required(VERSION 3.15)
project(test_mtdev C)

# Find the package via Conan-generated CMakeDeps
find_package(mtdev REQUIRED)

add_executable(test_mtdev test.c)
target_link_libraries(test_mtdev mtdev::mtdev)

enable_testing()
add_test(NAME test_mtdev COMMAND test_mtdev)
