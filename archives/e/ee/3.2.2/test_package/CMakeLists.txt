cmake_minimum_required(VERSION 3.15)
project(test_ee C)

# Find the package via Conan-generated CMakeDeps
find_package(ee REQUIRED)

add_executable(test_ee test.c)
target_link_libraries(test_ee ee::ee)

enable_testing()
add_test(NAME test_ee COMMAND test_ee)
