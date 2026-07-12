cmake_minimum_required(VERSION 3.15)
project(test_bstring C)

# Find the package via Conan-generated CMakeDeps
find_package(bstring REQUIRED)

add_executable(test_bstring test_bstring.c)
target_link_libraries(test_bstring bstring::bstring)

enable_testing()
add_test(NAME test_bstring COMMAND test_bstring)
