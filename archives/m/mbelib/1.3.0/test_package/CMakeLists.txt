cmake_minimum_required(VERSION 3.15)
project(test_mbelib C)

# Find the package via Conan-generated CMakeDeps
find_package(mbelib REQUIRED)

add_executable(test_mbelib test.c)
target_link_libraries(test_mbelib mbelib::mbelib)

enable_testing()
add_test(NAME test_mbelib COMMAND test_mbelib)
