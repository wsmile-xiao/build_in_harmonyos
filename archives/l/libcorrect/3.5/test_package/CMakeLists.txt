cmake_minimum_required(VERSION 3.15)
project(test_libcorrect C)

# Find the package via Conan-generated CMakeDeps
find_package(libcorrect REQUIRED)

add_executable(test_libcorrect test.c)
target_link_libraries(test_libcorrect libcorrect::libcorrect)

enable_testing()
add_test(NAME test_libcorrect COMMAND test_libcorrect)
