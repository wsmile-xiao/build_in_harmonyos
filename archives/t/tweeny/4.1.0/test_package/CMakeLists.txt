cmake_minimum_required(VERSION 3.15)
project(test_tweeny CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(Tweeny REQUIRED)

add_executable(test_tweeny test_tweeny.cpp)
target_link_libraries(test_tweeny tweeny::tweeny)

enable_testing()
add_test(NAME test_tweeny COMMAND test_tweeny)
