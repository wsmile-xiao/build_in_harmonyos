cmake_minimum_required(VERSION 3.15)
project(test_sword CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(sword REQUIRED)

add_executable(test_sword test.cpp)
target_link_libraries(test_sword sword::sword)

enable_testing()
add_test(NAME test_sword COMMAND test_sword)
