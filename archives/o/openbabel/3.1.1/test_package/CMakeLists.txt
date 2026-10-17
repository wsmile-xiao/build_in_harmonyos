cmake_minimum_required(VERSION 3.15)
project(test_openbabel CXX)

set(CMAKE_CXX_STANDARD 17)

# Find the package via Conan-generated CMakeDeps
find_package(openbabel REQUIRED)

add_executable(test_openbabel test_openbabel.cpp)
target_link_libraries(test_openbabel openbabel::openbabel)

enable_testing()
add_test(NAME test_openbabel COMMAND test_openbabel)
