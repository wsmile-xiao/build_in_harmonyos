cmake_minimum_required(VERSION 3.15)
project(test_gtksourceview5 C)

# Find the package via Conan-generated CMakeDeps (cmake_file_name=gtksourceview-5).
find_package(gtksourceview-5 CONFIG REQUIRED)

add_executable(test_gtksourceview5 test.c)
target_link_libraries(test_gtksourceview5 gtksourceview-5::gtksourceview-5)

enable_testing()
add_test(NAME test_gtksourceview5 COMMAND test_gtksourceview5)
