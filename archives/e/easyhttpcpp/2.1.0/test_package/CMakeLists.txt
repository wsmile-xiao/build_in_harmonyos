cmake_minimum_required(VERSION 3.15)
project(test_easyhttpcpp CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(easyhttpcpp REQUIRED)
find_package(poco REQUIRED)

add_executable(test_easyhttpcpp test_easyhttpcpp.cpp)
target_link_libraries(test_easyhttpcpp easyhttpcpp::easyhttp)

enable_testing()
add_test(NAME test_easyhttpcpp COMMAND test_easyhttpcpp)