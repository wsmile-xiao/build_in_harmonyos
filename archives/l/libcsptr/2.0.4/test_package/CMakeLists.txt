cmake_minimum_required(VERSION 3.15)
project(test_libcsptr C)

# Find the package via Conan-generated CMakeDeps
find_package(libcsptr REQUIRED)

add_executable(test_libcsptr test.c)
target_link_libraries(test_libcsptr libcsptr::libcsptr)

enable_testing()
add_test(NAME test_libcsptr COMMAND test_libcsptr)
