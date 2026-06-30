cmake_minimum_required(VERSION 3.15)
project(test_grommunio-error-pages C)

# Find the package via Conan-generated CMakeDeps
find_package(grommunio-error-pages REQUIRED)

add_executable(test_grommunio-error-pages test.c)
target_link_libraries(test_grommunio-error-pages grommunio-error-pages::grommunio-error-pages)

enable_testing()
add_test(NAME test_grommunio-error-pages COMMAND test_grommunio-error-pages)
