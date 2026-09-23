cmake_minimum_required(VERSION 3.15)
project(test_libndp C)

# Find the package via Conan-generated CMakeDeps
find_package(libndp REQUIRED)

add_executable(test_libndp test.c)
target_link_libraries(test_libndp libndp::libndp)

enable_testing()
add_test(NAME test_libndp COMMAND test_libndp)
