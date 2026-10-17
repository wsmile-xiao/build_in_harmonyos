cmake_minimum_required(VERSION 3.15)
project(test_fmi-ls-bus C)

# Find the package via Conan-generated CMakeDeps
find_package(fmi-ls-bus REQUIRED)

add_executable(test_fmi-ls-bus test.c)
target_link_libraries(test_fmi-ls-bus fmi-ls-bus::fmi-ls-bus)

enable_testing()
add_test(NAME test_fmi-ls-bus COMMAND test_fmi-ls-bus)
