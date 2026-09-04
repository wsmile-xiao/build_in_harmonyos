cmake_minimum_required(VERSION 3.15)
project(test_maddy LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(maddy REQUIRED)

add_executable(test_maddy test.cpp)
target_link_libraries(test_maddy maddy::maddy)

enable_testing()
add_test(NAME test_maddy COMMAND test_maddy)