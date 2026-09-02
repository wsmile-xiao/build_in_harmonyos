cmake_minimum_required(VERSION 3.15)
project(test_libtermkey C)

# Find the package via Conan-generated CMakeDeps
find_package(libtermkey REQUIRED)

add_executable(test_libtermkey test.c)
target_link_libraries(test_libtermkey libtermkey::libtermkey)

enable_testing()
add_test(NAME test_libtermkey COMMAND test_libtermkey)
