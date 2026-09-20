cmake_minimum_required(VERSION 3.15)
project(test_serialdv CXX)

# Find the package via Conan-generated CMakeDeps
find_package(serialdv REQUIRED)

add_executable(test_serialdv test_serialdv.cpp)
target_link_libraries(test_serialdv serialdv::serialdv)
set_property(TARGET test_serialdv PROPERTY CXX_STANDARD 11)
set_property(TARGET test_serialdv PROPERTY CXX_STANDARD_REQUIRED ON)

enable_testing()
add_test(NAME test_serialdv COMMAND test_serialdv)
