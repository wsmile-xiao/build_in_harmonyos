cmake_minimum_required(VERSION 3.15)
project(test_muparser CXX)

# Find the package via Conan-generated CMakeDeps
find_package(muparser REQUIRED)

add_executable(test_muparser test.cpp)
target_link_libraries(test_muparser muparser::muparser)

enable_testing()
add_test(NAME test_muparser COMMAND test_muparser)
