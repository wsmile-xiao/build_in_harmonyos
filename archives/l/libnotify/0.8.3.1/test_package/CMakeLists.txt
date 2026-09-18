cmake_minimum_required(VERSION 3.15)
project(test_libnotify C)

# Find the package via Conan-generated CMakeDeps
find_package(libnotify REQUIRED)

add_executable(test_libnotify test_package.c)
target_link_libraries(test_libnotify libnotify::libnotify)

enable_testing()
add_test(NAME test_libnotify COMMAND test_libnotify)
