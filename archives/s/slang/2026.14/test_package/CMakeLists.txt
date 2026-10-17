cmake_minimum_required(VERSION 3.15)
project(test_slang CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(slang REQUIRED)

add_executable(test_slang test.cpp)
target_link_libraries(test_slang slang::slang)

enable_testing()
add_test(NAME test_slang COMMAND test_slang)
