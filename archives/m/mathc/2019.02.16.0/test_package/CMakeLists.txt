cmake_minimum_required(VERSION 3.15)
project(test_mathc C)

# Find the package via Conan-generated CMakeDeps
find_package(mathc REQUIRED)

add_executable(test_mathc harmonyos_test.c)
target_link_libraries(test_mathc mathc::mathc)
target_link_libraries(test_mathc m)

enable_testing()
add_test(NAME test_mathc COMMAND test_mathc)