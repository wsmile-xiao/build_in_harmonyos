cmake_minimum_required(VERSION 3.15)
project(test_gnucobol C)

# Find the package via Conan-generated CMakeDeps
find_package(gnucobol REQUIRED)

add_executable(test_gnucobol test.c)
target_link_libraries(test_gnucobol gnucobol::gnucobol)

enable_testing()
add_test(NAME test_gnucobol COMMAND test_gnucobol)
