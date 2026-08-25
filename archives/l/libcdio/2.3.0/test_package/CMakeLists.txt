cmake_minimum_required(VERSION 3.15)
project(test_libcdio C)

# Find the package via Conan-generated CMakeDeps
find_package(libcdio CONFIG REQUIRED)

add_executable(test_libcdio test.c)
target_link_libraries(test_libcdio libcdio::libcdio)

enable_testing()
add_test(NAME test_libcdio COMMAND test_libcdio)
