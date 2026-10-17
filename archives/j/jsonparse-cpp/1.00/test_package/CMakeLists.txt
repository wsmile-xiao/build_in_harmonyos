cmake_minimum_required(VERSION 3.15)
project(test_jsonparse-cpp C)

# Find the package via Conan-generated CMakeDeps
find_package(jsonparse-cpp REQUIRED)

add_executable(test_jsonparse-cpp test.c)
target_link_libraries(test_jsonparse-cpp jsonparse-cpp::jsonparse-cpp)

enable_testing()
add_test(NAME test_jsonparse-cpp COMMAND test_jsonparse-cpp)
