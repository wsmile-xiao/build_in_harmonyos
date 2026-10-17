cmake_minimum_required(VERSION 3.15)
project(test_libdecaf C)

# Find the package via Conan-generated CMakeDeps
find_package(libdecaf REQUIRED)

add_executable(test_libdecaf test_decaf_api.c)
target_link_libraries(test_libdecaf libdecaf::libdecaf)

enable_testing()
add_test(NAME test_libdecaf COMMAND test_libdecaf)
