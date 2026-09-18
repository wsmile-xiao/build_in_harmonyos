cmake_minimum_required(VERSION 3.15)
project(test_libpgf CXX)

# Find the package via Conan-generated CMakeDeps
find_package(libpgf REQUIRED)

add_executable(test_libpgf test_libpgf.cpp)
target_link_libraries(test_libpgf libpgf::libpgf)

enable_testing()
add_test(NAME test_libpgf COMMAND test_libpgf)
