cmake_minimum_required(VERSION 3.15)
project(test_fancyargumentparser CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(fancyargumentparser REQUIRED)

add_executable(test_fancyargumentparser test.cpp)
target_link_libraries(test_fancyargumentparser fancyargumentparser::fancyargumentparser)

enable_testing()
add_test(NAME test_fancyargumentparser COMMAND test_fancyargumentparser)