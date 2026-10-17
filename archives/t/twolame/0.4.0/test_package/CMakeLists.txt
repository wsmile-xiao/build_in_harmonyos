cmake_minimum_required(VERSION 3.15)
project(test_twolame C)

# Find the package via Conan-generated CMakeDeps
find_package(twolame REQUIRED)

add_executable(test_twolame test.c)
target_link_libraries(test_twolame twolame::twolame)

enable_testing()
add_test(NAME test_twolame COMMAND test_twolame)
