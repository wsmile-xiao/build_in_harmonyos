cmake_minimum_required(VERSION 3.15)
project(test_csv2 CXX)

# Find the package via Conan-generated CMakeDeps
find_package(csv2 REQUIRED)

add_executable(test_csv2 test_csv2.cpp)
target_link_libraries(test_csv2 PRIVATE csv2::csv2)
set_target_properties(test_csv2 PROPERTIES CXX_STANDARD 17)

enable_testing()
add_test(NAME test_csv2 COMMAND test_csv2)
