cmake_minimum_required(VERSION 3.15)
project(test_cppcodec CXX)

# Find the package via Conan-generated CMakeDeps
find_package(cppcodec REQUIRED)

add_executable(test_cppcodec test_cppcodec.cpp)
target_link_libraries(test_cppcodec cppcodec::cppcodec)

enable_testing()
add_test(NAME test_cppcodec COMMAND test_cppcodec)