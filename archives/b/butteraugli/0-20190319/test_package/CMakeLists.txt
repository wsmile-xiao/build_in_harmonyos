cmake_minimum_required(VERSION 3.15)
project(test_butteraugli CXX)

# Find the package via Conan-generated CMakeDeps
find_package(butteraugli REQUIRED)

add_executable(test_butteraugli test.cpp)
target_link_libraries(test_butteraugli butteraugli::butteraugli)

enable_testing()
add_test(NAME test_butteraugli COMMAND test_butteraugli)