cmake_minimum_required(VERSION 3.15)
project(test_librevenge CXX)

# Find the package via Conan-generated CMakeDeps
find_package(librevenge REQUIRED)

add_executable(test_librevenge test.cpp)
target_link_libraries(test_librevenge librevenge::librevenge)

enable_testing()
add_test(NAME test_librevenge COMMAND test_librevenge)
