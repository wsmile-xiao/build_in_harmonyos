cmake_minimum_required(VERSION 3.15)
project(test_libharu C)

# Find the package via Conan-generated CMakeDeps
find_package(libharu REQUIRED)

add_executable(test_libharu test.c)
target_link_libraries(test_libharu libharu::libharu)

enable_testing()
add_test(NAME test_libharu COMMAND test_libharu)
