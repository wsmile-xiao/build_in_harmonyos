cmake_minimum_required(VERSION 3.15)
project(test_uinputplus CXX)

# Find the package via Conan-generated CMakeDeps
find_package(uInputPlus REQUIRED)

add_executable(test_uinputplus test_uinputplus.cpp)
target_link_libraries(test_uinputplus uInputPlus::uInputPlus)

enable_testing()
add_test(NAME test_uinputplus COMMAND test_uinputplus)
