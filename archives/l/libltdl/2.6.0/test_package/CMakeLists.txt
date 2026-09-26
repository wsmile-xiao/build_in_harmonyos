cmake_minimum_required(VERSION 3.15)
project(test_libltdl C)

# Find the package via Conan-generated CMakeDeps
find_package(libltdl REQUIRED)

add_executable(test_libltdl test.c)
target_link_libraries(test_libltdl libltdl::libltdl)

enable_testing()
add_test(NAME test_libltdl COMMAND test_libltdl)
