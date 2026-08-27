cmake_minimum_required(VERSION 3.15)
project(test_opencore_amr C)

# Find the package via Conan-generated CMakeDeps
find_package(opencore-amr REQUIRED)

add_executable(test_opencore_amr test.c)
target_link_libraries(test_opencore_amr opencore-amr::amrnb opencore-amr::amrwb)

enable_testing()
add_test(NAME test_opencore_amr COMMAND test_opencore_amr)
