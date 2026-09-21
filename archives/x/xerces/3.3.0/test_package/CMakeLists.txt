cmake_minimum_required(VERSION 3.15)
project(test_xerces CXX)

# Find xerces-c via the Conan-generated CMakeDeps package.
find_package(xerces-c CONFIG REQUIRED)

add_executable(test_xerces test.cpp)
target_link_libraries(test_xerces PRIVATE xerces-c::xerces-c)
set_target_properties(test_xerces PROPERTIES CXX_STANDARD 14)

enable_testing()
add_test(NAME test_xerces COMMAND test_xerces)
