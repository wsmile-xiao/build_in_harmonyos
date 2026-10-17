cmake_minimum_required(VERSION 3.15)
project(test_nng C)

# Find the package via Conan-generated CMakeDeps
find_package(nng REQUIRED)

add_executable(test_nng test.c)
target_link_libraries(test_nng nng::nng)

enable_testing()
add_test(NAME test_nng COMMAND test_nng)
