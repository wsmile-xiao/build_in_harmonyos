cmake_minimum_required(VERSION 3.15)
project(test_libnss-cache C)

# Find the package via Conan-generated CMakeDeps
find_package(libnss-cache REQUIRED)

add_executable(test_libnss-cache test.c)
target_link_libraries(test_libnss-cache libnss-cache::libnss-cache)

enable_testing()
add_test(NAME test_libnss-cache COMMAND test_libnss-cache)
