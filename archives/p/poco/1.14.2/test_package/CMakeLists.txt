cmake_minimum_required(VERSION 3.15)
project(test_poco CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(Poco REQUIRED)

add_executable(test_poco test.cpp)
target_link_libraries(test_poco Poco::Poco)

enable_testing()
add_test(NAME test_poco COMMAND test_poco)
