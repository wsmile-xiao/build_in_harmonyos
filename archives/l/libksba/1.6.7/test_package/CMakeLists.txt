cmake_minimum_required(VERSION 3.15)
project(test_libksba C)

# Find the package via Conan-generated CMakeDeps
find_package(libksba REQUIRED)

add_executable(test_libksba test.c)
target_link_libraries(test_libksba libksba::libksba)

enable_testing()
add_test(NAME test_libksba COMMAND test_libksba)
