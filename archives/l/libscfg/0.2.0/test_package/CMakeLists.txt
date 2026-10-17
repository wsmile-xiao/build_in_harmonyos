cmake_minimum_required(VERSION 3.15)
project(test_scfg C)

# Find the package via Conan-generated CMakeDeps
find_package(libscfg REQUIRED)

add_executable(test_scfg test_scfg.c)
target_link_libraries(test_scfg libscfg::libscfg)

enable_testing()
add_test(NAME test_scfg COMMAND test_scfg)
