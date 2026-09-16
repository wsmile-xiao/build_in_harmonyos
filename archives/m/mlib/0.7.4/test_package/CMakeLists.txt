cmake_minimum_required(VERSION 3.15)
project(test_mlib C)

# Find the package via Conan-generated CMakeDeps
find_package(mlib REQUIRED)

add_executable(test_mlib test_mlib.c)
target_link_libraries(test_mlib mlib::mlib)
set_target_properties(test_mlib PROPERTIES C_STANDARD 99)

enable_testing()
add_test(NAME test_mlib COMMAND test_mlib)
