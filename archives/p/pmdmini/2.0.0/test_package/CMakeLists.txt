cmake_minimum_required(VERSION 3.15)
project(test_pmdmini CXX)

# Find the package via Conan-generated CMakeDeps
find_package(pmdmini REQUIRED)

add_executable(test_pmdmini test.cpp)
target_link_libraries(test_pmdmini PRIVATE pmdmini::pmdmini)

enable_testing()
add_test(NAME test_pmdmini COMMAND test_pmdmini)
