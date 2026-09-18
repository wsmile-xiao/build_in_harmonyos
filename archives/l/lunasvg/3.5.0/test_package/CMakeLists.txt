cmake_minimum_required(VERSION 3.15)
project(test_lunasvg CXX)

# Find the package via Conan-generated CMakeDeps
find_package(lunasvg REQUIRED)

add_executable(test_lunasvg test.cpp)
target_link_libraries(test_lunasvg lunasvg::lunasvg)

enable_testing()
add_test(NAME test_lunasvg COMMAND test_lunasvg)
