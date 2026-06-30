cmake_minimum_required(VERSION 3.15)
project(test_libpagemaker C)

# Find the package via Conan-generated CMakeDeps
find_package(libpagemaker REQUIRED)

add_executable(test_libpagemaker test.c)
target_link_libraries(test_libpagemaker libpagemaker::libpagemaker)

enable_testing()
add_test(NAME test_libpagemaker COMMAND test_libpagemaker)
