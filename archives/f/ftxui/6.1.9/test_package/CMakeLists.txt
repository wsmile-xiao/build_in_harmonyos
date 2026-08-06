cmake_minimum_required(VERSION 3.15)
project(test_ftxui CXX)

# Find the package via Conan-generated CMakeDeps
find_package(ftxui REQUIRED)

add_executable(test_ftxui test_ftxui.cpp)
target_link_libraries(test_ftxui ftxui::ftxui)

enable_testing()
add_test(NAME test_ftxui COMMAND test_ftxui)
