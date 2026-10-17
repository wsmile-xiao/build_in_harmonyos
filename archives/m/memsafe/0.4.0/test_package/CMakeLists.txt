cmake_minimum_required(VERSION 3.15)
project(test_memsafe CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(memsafe REQUIRED)

add_executable(test_memsafe test.cpp)
target_link_libraries(test_memsafe memsafe::memsafe)

enable_testing()
add_test(NAME test_memsafe COMMAND test_memsafe)
