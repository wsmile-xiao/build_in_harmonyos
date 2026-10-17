cmake_minimum_required(VERSION 3.15)
project(test_libtiff C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=TIFF)
find_package(TIFF REQUIRED)

add_executable(test_libtiff test.c)
target_link_libraries(test_libtiff TIFF::tiff)

enable_testing()
add_test(NAME test_libtiff COMMAND test_libtiff)
