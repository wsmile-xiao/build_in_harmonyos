cmake_minimum_required(VERSION 3.15)
project(test_gsmlib CXX)

# Find the package via Conan-generated CMakeDeps
find_package(gsmlib REQUIRED)

add_executable(test_gsmlib test_gsmlib.cpp)
target_link_libraries(test_gsmlib gsmlib::gsmlib)

enable_testing()
add_test(NAME test_gsmlib COMMAND test_gsmlib)