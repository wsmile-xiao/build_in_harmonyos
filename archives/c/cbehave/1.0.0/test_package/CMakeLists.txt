cmake_minimum_required(VERSION 3.15)
project(test_cbehave C)

# Find the package via Conan-generated CMakeDeps
find_package(cbehave REQUIRED)

add_executable(test_cbehave test.c)
target_link_libraries(test_cbehave cbehave::cbehave)

enable_testing()
add_test(NAME test_cbehave COMMAND test_cbehave)
