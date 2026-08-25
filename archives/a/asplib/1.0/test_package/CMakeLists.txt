cmake_minimum_required(VERSION 3.15)
project(test_asplib CXX)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(asplib REQUIRED)

add_executable(test_asplib test.cpp)
target_link_libraries(test_asplib asplib::asplib)

enable_testing()
add_test(NAME test_asplib COMMAND test_asplib)
