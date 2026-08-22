cmake_minimum_required(VERSION 3.15)
project(test_gts C)

# Find the package via Conan-generated CMakeDeps
find_package(gts REQUIRED)

add_executable(test_gts test.c)
target_link_libraries(test_gts gts::gts)

enable_testing()
add_test(NAME test_gts COMMAND test_gts)
