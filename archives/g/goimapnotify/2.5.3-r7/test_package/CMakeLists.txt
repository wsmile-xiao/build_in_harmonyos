cmake_minimum_required(VERSION 3.15)
project(test_goimapnotify C)

# Find the package via Conan-generated CMakeDeps
find_package(goimapnotify REQUIRED)

add_executable(test_goimapnotify test.c)
target_link_libraries(test_goimapnotify goimapnotify::goimapnotify)

enable_testing()
add_test(NAME test_goimapnotify COMMAND test_goimapnotify)
