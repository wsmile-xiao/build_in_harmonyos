cmake_minimum_required(VERSION 3.15)
project(test_exiv2 CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(exiv2 REQUIRED)

add_executable(test_exiv2 test_exiv2.cpp)
target_link_libraries(test_exiv2 exiv2::exiv2)

enable_testing()
add_test(NAME test_exiv2 COMMAND test_exiv2)
