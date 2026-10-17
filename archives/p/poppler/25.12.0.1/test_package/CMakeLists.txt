cmake_minimum_required(VERSION 3.15)
project(test_poppler CXX)

# Find the package via Conan-generated CMakeDeps
find_package(poppler REQUIRED)

add_executable(test_poppler test.cpp)
target_link_libraries(test_poppler poppler::poppler)

enable_testing()
add_test(NAME test_poppler COMMAND test_poppler)
