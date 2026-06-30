cmake_minimum_required(VERSION 3.15)
project(test_rolldice C)

# Find the package via Conan-generated CMakeDeps
find_package(rolldice REQUIRED)

add_executable(test_rolldice test.c)
target_link_libraries(test_rolldice rolldice::rolldice)

enable_testing()
add_test(NAME test_rolldice COMMAND test_rolldice)
