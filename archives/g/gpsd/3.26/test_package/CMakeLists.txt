cmake_minimum_required(VERSION 3.15)
project(test_gpsd C)

# Find the package via Conan-generated CMakeDeps
find_package(gpsd REQUIRED)

add_executable(test_gpsd test.c)
target_link_libraries(test_gpsd gpsd::gpsd)

enable_testing()
add_test(NAME test_gpsd COMMAND test_gpsd)
