cmake_minimum_required(VERSION 3.15)
project(test_refl-cpp CXX)

# refl-cpp requires C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find the package via Conan-generated CMakeDeps
find_package(refl-cpp REQUIRED)

add_executable(test_refl-cpp test.cpp)
target_link_libraries(test_refl-cpp refl-cpp::refl-cpp)

enable_testing()
add_test(NAME test_refl-cpp COMMAND test_refl-cpp)