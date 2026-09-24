cmake_minimum_required(VERSION 3.15)
project(test_jsonxx CXX)

# Find the package via Conan-generated CMakeDeps
find_package(jsonxx REQUIRED)

add_executable(test_jsonxx test_jsonxx.cpp)
target_link_libraries(test_jsonxx jsonxx::jsonxx)

enable_testing()
add_test(NAME test_jsonxx COMMAND test_jsonxx)