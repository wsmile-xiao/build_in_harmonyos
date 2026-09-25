cmake_minimum_required(VERSION 3.15)
project(test_ffc C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name = ffc)
find_package(ffc REQUIRED)

add_executable(test_ffc test.c)
target_link_libraries(test_ffc ffc::ffc)

enable_testing()
add_test(NAME test_ffc COMMAND test_ffc)
