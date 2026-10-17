cmake_minimum_required(VERSION 3.15)
project(test_mpdecimal CXX)

# Find the package via Conan-generated CMakeDeps
find_package(mpdecimal REQUIRED)

add_executable(test_mpdecimal test.cpp)
target_link_libraries(test_mpdecimal mpdecimal::mpdecimal mpdecimal::mpdecpp)

enable_testing()
add_test(NAME test_mpdecimal COMMAND test_mpdecimal)