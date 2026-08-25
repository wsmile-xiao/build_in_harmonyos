cmake_minimum_required(VERSION 3.15)
project(test_libgfshare LANGUAGES C)

# Find the Conan-packaged libgfshare via CMakeDeps
find_package(libgfshare CONFIG REQUIRED)

add_executable(test_libgfshare test.c)
target_link_libraries(test_libgfshare PRIVATE libgfshare::libgfshare)

enable_testing()
add_test(NAME test_libgfshare COMMAND test_libgfshare)
