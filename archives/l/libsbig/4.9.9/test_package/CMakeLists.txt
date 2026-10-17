cmake_minimum_required(VERSION 3.15)
project(test_libsbig C)

# Find the package via Conan-generated CMakeDeps (libsbig-config.cmake)
find_package(libsbig REQUIRED CONFIG)

add_executable(test_libsbig test.c)
target_link_libraries(test_libsbig PRIVATE libsbig::libsbig)

enable_testing()
add_test(NAME libsbig_consumer COMMAND test_libsbig)

