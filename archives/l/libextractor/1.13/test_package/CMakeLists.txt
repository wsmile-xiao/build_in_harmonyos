cmake_minimum_required(VERSION 3.15)
project(test_libextractor C)

# Find the package via Conan-generated CMakeDeps
find_package(libextractor REQUIRED)

add_executable(test_libextractor test.c)
target_link_libraries(test_libextractor libextractor::libextractor)

enable_testing()
add_test(NAME test_libextractor COMMAND test_libextractor)
