cmake_minimum_required(VERSION 3.15)
project(test_libpuzzle C)

# Consumer headers/libs come from the Conan-generated configs
find_package(libpuzzle REQUIRED)
find_package(gd REQUIRED)

add_executable(test_libpuzzle test_libpuzzle.c)
target_link_libraries(test_libpuzzle PRIVATE libpuzzle::libpuzzle gd::gd)

enable_testing()
add_test(NAME test_libpuzzle COMMAND test_libpuzzle ${CMAKE_CURRENT_BINARY_DIR})
