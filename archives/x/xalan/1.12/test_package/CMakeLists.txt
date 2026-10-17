cmake_minimum_required(VERSION 3.15)
project(test_xalan CXX)

# Find XalanC via the Conan-generated CMakeDeps package.
find_package(XalanC CONFIG REQUIRED)

add_executable(test_xalan test.cpp)
target_link_libraries(test_xalan PRIVATE XalanC::XalanC)
set_target_properties(test_xalan PROPERTIES CXX_STANDARD 14)

enable_testing()
add_test(NAME test_xalan COMMAND test_xalan)
