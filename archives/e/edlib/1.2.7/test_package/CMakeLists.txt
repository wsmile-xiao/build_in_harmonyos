cmake_minimum_required(VERSION 3.15)
project(test_edlib CXX)

# Find the package via Conan-generated CMakeDeps
find_package(edlib REQUIRED)

add_executable(test_edlib harmonyos_test.cpp)
target_link_libraries(test_edlib edlib::edlib)

enable_testing()
add_test(NAME test_edlib COMMAND test_edlib)
