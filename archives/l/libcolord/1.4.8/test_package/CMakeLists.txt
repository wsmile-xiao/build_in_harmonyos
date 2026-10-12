cmake_minimum_required(VERSION 3.15)
project(test_libcolord C)

# Find the package via Conan-generated CMakeDeps
find_package(libcolord REQUIRED)

add_executable(test_libcolord test.c)
target_link_libraries(test_libcolord libcolord::libcolord)

enable_testing()
add_test(NAME test_libcolord COMMAND test_libcolord)
