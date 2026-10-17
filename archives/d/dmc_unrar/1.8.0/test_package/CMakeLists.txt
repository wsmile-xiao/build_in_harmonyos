cmake_minimum_required(VERSION 3.15)
project(test_dmc_unrar C)

# Find the package via Conan-generated CMakeDeps
find_package(dmc_unrar REQUIRED)

add_executable(test_dmc_unrar test.c)
target_link_libraries(test_dmc_unrar dmc_unrar::dmc_unrar)

enable_testing()
add_test(NAME test_dmc_unrar COMMAND test_dmc_unrar)
