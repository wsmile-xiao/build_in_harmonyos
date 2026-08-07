cmake_minimum_required(VERSION 3.15)
project(test_libabigail CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libabigail REQUIRED)

add_executable(test_libabigail test_libabigail.cc)
target_link_libraries(test_libabigail libabigail::libabigail)

enable_testing()
add_test(NAME test_libabigail COMMAND test_libabigail)
