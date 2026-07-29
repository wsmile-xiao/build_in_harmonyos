cmake_minimum_required(VERSION 3.15)
project(test_wxwidgets CXX)

# Find the package via Conan-generated CMakeDeps
find_package(wxWidgets REQUIRED)

add_executable(test_wxwidgets test.cpp)
target_link_libraries(test_wxwidgets wxWidgets::wxWidgets)

enable_testing()
add_test(NAME test_wxwidgets COMMAND test_wxwidgets)
