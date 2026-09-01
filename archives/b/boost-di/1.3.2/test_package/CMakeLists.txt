cmake_minimum_required(VERSION 3.15)
project(test_boost_di CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(boost-di REQUIRED)

add_executable(test_boost_di test_di.cpp)
target_link_libraries(test_boost_di boost-di::boost-di)

enable_testing()
add_test(NAME test_boost_di COMMAND test_boost_di)
